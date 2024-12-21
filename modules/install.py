from io import StringIO
import os
from os import path as op
import re
from shlex import quote
import subprocess
import time
from typing import Any, Callable, TYPE_CHECKING
if TYPE_CHECKING:
    import argparse

from .. import logger, get_config_dict, get_config_str, CONFIG


COMMANDS = {
    'install': 'Install app',
    'start': 'Start app',
    'stop': 'Stop app',
    'restart': 'Restart app',
    'reload': 'Reload app'
}


SCRIPTS_SUBDIR = 'install_scripts'
SCRIPTS_DIR = op.join(op.dirname(op.dirname(__file__)), SCRIPTS_SUBDIR)


def sjoin(split_command: list[str]):
    """Return a shell-escaped string from *split_command*."""
    return ' '.join(quote(arg) for arg in split_command)


def get_revision():
    res = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True)
    if res.returncode == 0:
        return res.stdout[:7].decode('utf-8')
    return time.strftime('%Y%m$d')


def _do_rsync(src: str, dst: str, excl: list[str], incl: list[str]):
    cmd = ['rsync', '-a', '--update', '--delete', '--filter=:- .gitignore']
    cmd.extend(f'--exclude={elem}' for elem in excl if elem)
    cmd.extend(f'--include={elem}' for elem in incl if elem)
    cmd.extend([src, dst])
    logger.info('Running: %s %s', cmd[0], ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd[1:]))
    return subprocess.run(cmd)


def _install_config(host: str | None = None):
    config = get_config_dict('INSTALL.')
    if host:
        config.update(dict(get_config_dict(f'INSTALL_{host}.')))
    return config


def _get_scripts_loc(rootdir: str):
    abs_scripts, abs_root = (op.realpath(SCRIPTS_DIR), op.realpath(rootdir))
    if not abs_scripts.startswith(abs_root + '/'):
        logger.warning('Runlib is outside the rootdir (%s), install may fail', abs_root)
        scripts_loc = f'''"$(python3 -c 'import runlib, os; print(os.path.dirname(runlib.__file__))')/{SCRIPTS_SUBDIR}"'''
    else:
        scripts_loc = abs_scripts[len(abs_root)+1:]
    return scripts_loc


def do_install(rootdir: str, dest: str, subdir: str, revision: str, filter_cmd: Callable[[str], list[str]], options: dict[str, Any]):
    venv_dir = get_config_str('VENV.DIR')
    rootdir, dest = rootdir.rstrip('/'), dest.rstrip('/')
    excludes = [venv_dir, '.git']
    excludes.extend(options['excludes'])
    includes: list[str] = []
    includes.extend(options['includes'])
    moves = {
        f'{rootdir}/{src.strip("/")}/': f'_installed_/{dst.strip("/")}/'
        for src, dst in options['moves'].items()}

    if options.get('build'):
        logger.info('Calling build cmd')
        subprocess.run(options['build'], shell=True)
        logger.info('Build cmd done')
    with open(op.join(SCRIPTS_DIR, 'install.sh')) as install_script:
        cmd = install_script.read().format(subdir=subdir, revision=revision, **{
            key: quote(str(val)) for key, val in options.items()})
    subprocess.run(filter_cmd(cmd))

    _do_rsync(f'{rootdir}/', f'{dest}/_installed_/', excludes + list(moves.keys()), includes)
    if moves:
        cmd = '\n'.join(
            f'mkdir -pv "$(dirname {quote(subdir)}/{quote(dst)})"'
            for dst in moves.values())
        subprocess.run(filter_cmd(cmd))
    for src, dst in moves.items():
        _do_rsync(src, op.join(dest, dst), excludes, includes + [src])


def do_relink(
    subdir: str,
    filter_cmd: Callable[[str], list[str]],
    stage: str,
    commands: tuple[str, str, str],
    install_env: dict[str, str] | None = None,
):
    start_cmd, upgrade_cmd, stop_cmd = commands
    venv_dir = get_config_str('VENV.DIR')
    req_file = get_config_str('VENV.REQUIREMENTS')
    logger.info('Relinking installed app: %s to %s', subdir, stage)
    with open(op.join(SCRIPTS_DIR, 'prepare.sh')) as prepare_script:
        prepare_cmd = prepare_script.read().format(venv_dir=quote(venv_dir), req_file=quote(req_file))
    if install_env:
        try:
            CONFIG['ENVIRONMENT'].update(install_env)
        except KeyError:
            CONFIG['ENVIRONMENT'] = install_env
        config_location = CONFIG['MAIN']['CONFIG']
        with StringIO() as sfile:
            del CONFIG['MAIN']['ROOTDIR']
            del CONFIG['MAIN']['CONFIG']
            CONFIG.write(sfile)
            config_data = sfile.getvalue()
        delim = '__EOF'
        while f'\n{delim}\n' in config_data:
            delim += '_'
        prepare_cmd += f'cat <<"{delim}" > {config_location}\n{config_data}\n{delim}\n'

    stop_cmd = stop_cmd.replace("\n", "\n    ")
    script_vars = {
        'subdir': quote(subdir),
        'stage': quote(stage),
        'venv_dir': quote(venv_dir),
        'stop_cmd': stop_cmd,
        'prepare_cmd': prepare_cmd,
        'upgrade_cmd': upgrade_cmd,
        'start_cmd': start_cmd
    }
    with open(op.join(SCRIPTS_DIR, 'relink.sh')) as relink_script:
        cmd = relink_script.read().format(**script_vars)
    subprocess.run(filter_cmd(cmd))


def cmd_install(args: 'argparse.Namespace'):
    rootdir = get_config_str('ROOTDIR')
    scripts_loc = _get_scripts_loc(rootdir)
    host, _, subdir = args.dest.rpartition(':')
    subdir = subdir.rstrip('/')
    if host:
        filter_cmd: Callable[[str], list[str]] = lambda cmd: ['ssh', host, 'bash', '-c', quote(cmd)]
    else:
        filter_cmd: Callable[[str], list[str]] = lambda cmd: ['bash', '-c', cmd]

    config = _install_config(host)
    install_env = {var[4:]: value for var, value in config.items() if var.startswith('ENV_')}
    install_env['INSTALL_HOST'] = host or ''
    install_conf = {
        'build': config.get('BUILD_CMD', get_config_str('MAIN.BUILD_CMD')) if not args.skip_build else None,
        'clean': args.clean,
        'replace': args.replace,
        'excludes': re.split(r'\s+', config.get('EXCLUDE', '')),
        'includes': re.split(r'\s+', config.get('INCLUDE', '')),
        'moves': {src.strip(): dst.strip()
                  for elem in re.split(r'\n\s*', config.get('MOVE', ''))
                  for src, _, dst in (elem.partition(':'),) if src}
    }
    os.chdir(rootdir)
    revision = args.revision or get_revision()

    do_install(rootdir, args.dest, subdir, revision, filter_cmd, install_conf)
    if args.relink:
        start_cmd = args.start_cmd or config.get('START_CMD', f'. {scripts_loc}/start_cmd.sh')
        upgrade_cmd = args.upgrade_cmd or config.get('UPGRADE_CMD', '')
        stop_cmd = args.stop_cmd or config.get('STOP_CMD', f'. {scripts_loc}/stop_cmd.sh')
        do_relink(subdir, filter_cmd, stage=args.relink,
                  commands=(start_cmd, upgrade_cmd, stop_cmd), install_env=install_env)


def cmd_start(args: 'argparse.Namespace'):
    scripts_loc = _get_scripts_loc(get_config_str('ROOTDIR'))
    config = _install_config(get_config_str('ENVIRONMENT.INSTALL_HOST'))
    start_cmd = config.get('START_CMD', f'. {scripts_loc}/start_cmd.sh').rstrip()
    if args.arg:
        start_cmd += f' {sjoin(args.arg)}'
    logger.info('Starting app: %r', start_cmd)
    subprocess.run(['bash', '-c', start_cmd])


def cmd_stop(args: 'argparse.Namespace'):
    scripts_loc = _get_scripts_loc(get_config_str('ROOTDIR'))
    config = _install_config(get_config_str('ENVIRONMENT.INSTALL_HOST'))
    stop_cmd = config.get('STOP_CMD', f'. {scripts_loc}/stop_cmd.sh')
    if args:
        stop_cmd += f' {sjoin(args.arg)}'
    logger.info('Stopping app: %r', stop_cmd)
    subprocess.run(['bash', '-c', stop_cmd])


def cmd_restart(args: 'argparse.Namespace'):
    config = _install_config(get_config_str('ENVIRONMENT.INSTALL_HOST'))
    restart_cmd = config.get('RESTART_CMD')
    if restart_cmd:
        if args.arg:
            restart_cmd += f' {sjoin(args.arg)}'
        logger.info('Restarting app: %r', restart_cmd)
        subprocess.run(['bash', '-c', restart_cmd])
    else:
        logger.debug('No specific restart command, using stop/start')
        cmd_stop(args)
        time.sleep(1)
        cmd_start(args)


def cmd_reload(args: 'argparse.Namespace'):
    config = _install_config(get_config_str('ENVIRONMENT.INSTALL_HOST'))
    reload_cmd = config.get('RELOAD_CMD')
    if reload_cmd:
        if args.arg:
            reload_cmd += f' {sjoin(args.arg)}'
        logger.info('Reloading app: %r', reload_cmd)
        subprocess.run(['bash', '-c', reload_cmd])
    else:
        logger.debug('No specific reload command, using restart')
        cmd_restart(args)


def setup_parser(cmd: str, parser: 'argparse.ArgumentParser'):
    if cmd == 'install':
        parser.add_argument('dest', help='Install destination (scp uri)')
        parser.add_argument('-b', '--skip-build', action='store_true', default=False, help='Skip build step')
        parser.add_argument('--relink', action='store', nargs='?', const='current', help='Relink to installed version and restart. Argument is used as stage name (default: current)')
        parser.add_argument('--stop-cmd', help='Stop command (bash)')
        parser.add_argument('--upgrade-cmd', help='Upgrade command run before start (bash)')
        parser.add_argument('--start-cmd', help='Start command (bash)')
        parser.add_argument('-r', '--revision', help='Revision name (default: git-based/time-based)')
        parser.add_argument('--replace', action='store_true', default=False, help='Replace revision if exists')
        parser.add_argument('-c', '--clean', action='store_true', default=False,
                            help='Clean all revisons but the linked plus one newest')
        parser.set_defaults(call=cmd_install, use_venv=False)
    elif cmd == 'start':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_start, use_venv=False)
    elif cmd == 'stop':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_stop, use_venv=False)
    elif cmd == 'restart':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_restart, use_venv=False)
    elif cmd == 'reload':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_reload, use_venv=False)
