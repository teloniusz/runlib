from io import StringIO
import os
from os import path as op
import re
from shlex import quote
import subprocess
import sys
import time

from . import logger, get_config, CONFIG


SCRIPTS_SUBDIR = 'install_scripts'
SCRIPTS_DIR = op.join(op.dirname(__file__), SCRIPTS_SUBDIR)


def get_revision():
    res = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True)
    if res.returncode == 0:
        return res.stdout[:7].decode('utf-8')
    return time.strftime('%Y%m$d')


def _do_rsync(src, dst, excl, incl):
    cmd = ['rsync', '-a', '--update', '--delete', '--filter=:- .gitignore']
    cmd.extend(f'--exclude={elem}' for elem in excl if elem)
    cmd.extend(f'--include={elem}' for elem in incl if elem)
    cmd.extend([src, dst])
    logger.info('Running: %s %s', cmd[0], ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd[1:]))
    return subprocess.run(cmd)


def do_install(rootdir, dest, subdir, revision, filter_cmd, options):
    venv_dir = get_config('VENV.DIR')
    rootdir, dest = rootdir.rstrip('/'), dest.rstrip('/')
    excludes = [venv_dir, '.git']
    excludes.extend(options['excludes'])
    includes = []
    includes.extend(options['includes'])
    moves = {
        f'{rootdir}/{src.strip("/")}/': f'_installed_/{dst.strip("/")}/'
        for src, dst in options['moves'].items()}

    if 'build' in options:
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


def do_relink(subdir, filter_cmd, stage, commands, install_env=None):
    start_cmd, upgrade_cmd, stop_cmd = commands
    venv_dir = get_config('VENV.DIR')
    req_file = get_config('VENV.REQUIREMENTS')
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


def cmd_install(args):
    rootdir = get_config('ROOTDIR')

    abs_scripts, abs_root = (op.realpath(SCRIPTS_DIR), op.realpath(rootdir))
    if not abs_scripts.startswith(abs_root + '/'):
        logger.warning('Runlib is outside the rootdir (%s), install may fail', abs_root)
        scripts_loc = f'''"$(python3 -c 'import runlib, os; print os.path.dirname(runlib.__file__)')/{SCRIPTS_SUBDIR}"'''
    else:
        scripts_loc = abs_scripts[len(abs_root)+1:]

    host, _, subdir = args.dest.rpartition(':')
    subdir = subdir.rstrip('/')
    if host:
        filter_cmd = lambda cmd: ['ssh', host, 'bash', '-c', quote(cmd)]
    else:
        filter_cmd = lambda cmd: ['bash', '-c', cmd]

    config = get_config('INSTALL.')
    config.update(dict(get_config(f'INSTALL_{host}.')))
    install_env = {var[4:]: value for var, value in config.items() if var.startswith('ENV_')}
    install_conf = {
        'build': config.get('BUILD_CMD', get_config('MAIN.BUILD_CMD')) if not args.skip_build else None,
        'clean': args.clean,
        'replace': args.replace,
        'excludes': re.split('\s+', config.get('EXCLUDE', '')),
        'includes': re.split('\s+', config.get('INCLUDE', '')),
        'moves': {src.strip(): dst.strip()
                  for elem in re.split('\n\s*', config.get('MOVE', ''))
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


def setup_parser(parser):
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
