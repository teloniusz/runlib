import os
from os import path as op
import subprocess
import sys
import venv

from .. import get_config, logger


COMMANDS = {'env': 'Virtualenv management'}


def _find_or_create_venv(envpath):
    rootdir = get_config('ROOTDIR')

    if not envpath.startswith('/'):
        envpath = op.join(rootdir, envpath)
    if not op.isdir(envpath):
        logger.info('Virtual env not found, creating.')
        venv.create(envpath, with_pip=True)
        subprocess.check_call([op.join(envpath, 'bin', 'python'), '-m', 'pip', 'install', '--upgrade', 'pip'])
        req_file = op.join(rootdir, 'requirements.txt')
        if op.isfile(req_file):
            subprocess.check_call([op.join(envpath, 'bin', 'python'), '-m', 'pip', 'install', 'wheel'])
            subprocess.check_call([op.join(envpath, 'bin', 'python'), '-m', 'pip', 'install', '-r', req_file])
    return envpath


def _add_path(var, *args):
    paths = list(args) + var.split(':') if var else args
    existing = set()
    res = []
    for path in paths:
        if path not in existing:
            res.append(path)
            existing.add(path)
    return ':'.join(res)


def ensure_venv(envpath):
    current_env = os.environ.get('VIRTUAL_ENV', '')
    if not current_env or current_env != envpath:
        logger.info('Not in venv, entering.')
        envpath = _find_or_create_venv(envpath)
        interpreter = op.join(envpath, 'bin', 'python')
        if interpreter == sys.executable:
            raise RuntimeError(f'Already using interpreter: {interpreter}')
        env = os.environ.copy()
        env['PATH'] = _add_path(env.get('PATH'), op.join(envpath, 'bin'))
        env['PYTHONPATH'] = _add_path(env.get('PYTHONPATH'), get_config('ROOTDIR'))
        env['VIRTUAL_ENV'] = envpath
        env.pop('PYTHONHOME', None)

        logger.debug('Calling: %s with args: %r', interpreter, sys.argv)
        os.execle(interpreter, 'python', *sys.argv, env)


def shell(*args):
    rootdir = get_config('ROOTDIR')

    initscript = f'''. /etc/bash.bashrc;. ~/.bashrc
[[ -f {rootdir}/.bashrc.venv ]] && . {rootdir}/.bashrc.venv || PS1="[venv] $PS1"
export PATH={os.environ["PATH"]}\n'''
    rsync, wsync = os.pipe()
    rfd, wfd = os.pipe2(0)
    if os.fork():
        os.close(wfd)
        os.close(wsync)
        os.read(rsync, 1)
        os.execlp('bash', 'bash', '--rcfile', f'/dev/fd/{rfd}', *args)
    else:
        os.close(rfd)
        os.close(rsync)
        with os.fdopen(wfd, 'w') as wfile:
            wfile.write(initscript)
            os.write(wsync, b'\n')
        os.close(wsync)


def subcmd_freeze(req_filename, requirements, req_lines):
    for line in subprocess.check_output(['pip', 'freeze']).decode('utf-8').split('\n'):
        name, _, version = line.strip().partition('==')
        lower = name.lower()
        if lower in requirements:
            logger.debug('Found requirement: %s==%s', name, version)
            requirements[lower] = (version, name)
    with open(req_filename, 'w') as req_file:
        for line, name, version in req_lines:
            if name:
                lower = name.lower()
                version, orig = requirements.get(lower, (None, None))
                if version is not None:
                    req_file.write(f'{orig}=={version}\n' if version else f'{orig}\n')
                else:
                    req_file.write(f'{name}\n')
            else:
                req_file.write(line)


def subcmd_add(req_filename, requirements, req_lines, pkg):
    name = pkg.partition('==')[0]

    added = True
    idx = 0
    for idx, (line, lname, lversion) in enumerate(req_lines):
        if name.lower() <= lname.lower():
            if name.lower() == lname.lower():
                logger.info('Package already present in requirements, upgrading')
                prev_entry = lname if not lversion else f'{lname}=={lversion}'
                req_lines[idx] = (line.replace(prev_entry, pkg), lname, lversion)
                added = False
            break
    subprocess.check_call(['python', '-m', 'pip', 'install', '--upgrade', pkg])
    with open(req_filename, 'w') as req_file:
        if idx > 0:
            req_file.write(''.join(line for line, _, _ in req_lines[:idx]))
        if added:
            req_file.write(f'{pkg}\n')
        req_file.write(''.join(line for line, _, _ in req_lines[idx:]))


def subcmd_rm(req_filename, requirements, req_lines, pkg):
    if pkg.lower() not in requirements:
        logger.warning('Package not found: %s', pkg)
    else:
        subprocess.check_call(['python', '-m', 'pip', 'uninstall', pkg])
        with open(req_filename, 'w') as req_file:
            req_file.write(''.join(
                line
                for line, name, _ in req_lines
                if name.lower() != pkg.lower()))


def cmd_env(args):
    rootdir = get_config('ROOTDIR')

    req_filename = op.join(rootdir, get_config('VENV.REQUIREMENTS', 'requirements.txt'))
    req_lines = []
    requirements = {}
    try:
        with open(req_filename) as req_file:
            for line in req_file:
                record = line.strip().partition('#')[0]
                name, _, version = record.partition('==')
                req_lines.append((line, name, version))
                if name:
                    requirements[name.lower()] = (version, name)
    except IOError as exc:
        logger.warning('Cannot read requirements file: %s', exc)

    command = args.command or 'shell'
    if command == 'shell':
        shell(*(getattr(args, 'arg', ())))
    elif command == 'run':
        try:
            subprocess.check_call(args.arg)
        except subprocess.CalledProcessError as exc:
            logger.error('Called process returned %s', exc.returncode)
    elif command == 'update':
        os.execlp('python', 'python', '-m', 'pip', 'install', '-r', req_filename)
    elif command == 'list':
        print("\n".join(
            f'{orig}=={version}' if version else name
            for name, (version, orig) in requirements.items()) if requirements else "(requirements empty)")
    elif command == 'freeze':
        subcmd_freeze(req_filename, requirements, req_lines)
    elif command == 'add':
        subcmd_add(req_filename, requirements, req_lines, args.pkg.strip())
    elif command == 'rm':
        subcmd_rm(req_filename, requirements, req_lines, args.pkg.strip())


def setup_parser(cmd, parser):
    parser_sub = parser.add_subparsers(dest='command', help='Env command')
    parser_shell = parser_sub.add_parser('shell', help='Enter shell in virtualenv (default)')
    parser_shell.add_argument('arg', nargs='*')
    parser_run = parser_sub.add_parser('run', help='Run a command in virtualenv')
    parser_run.add_argument('arg', nargs='+')
    parser_update = parser_sub.add_parser('update', help='Update virtualenv')
    parser_add = parser_sub.add_parser('add', help='Add a package')
    parser_add.add_argument('pkg')
    parser_rm = parser_sub.add_parser('rm', help='Remove a package')
    parser_rm.add_argument('pkg')
    parser_list = parser_sub.add_parser('list', help='List packages')
    parser_freeze = parser_sub.add_parser('freeze', help='Freeze existing requirements')
    parser.set_defaults(command='shell', call=cmd_env)
