import os
from os import path as op
import subprocess
import sys

from . import get_config, logger


def cmd_uwsgi(args):
    rootdir = get_config('ROOTDIR')
    appmod = get_config('APPMOD')

    pidfile = op.join(rootdir, 'var', 'run', 'uwsgi.pid')
    logfile = op.join(rootdir, 'var', 'log', 'uwsgi.log')

    command = args.command
    if command == 'start':
        if op.isfile(pidfile):
            res = subprocess.run(['pgrep', '-F', pidfile], capture_output=True)
            if res.returncode == 0 and res.stdout:
                logger.error('Process still running')
                sys.exit(1)
        os.chdir(rootdir)
        os.makedirs(op.join('var', 'run'), mode=0o755, exist_ok=True)
        os.makedirs(op.join('var', 'log'), mode=0o755, exist_ok=True)
        socket = args.socket or op.join(rootdir, 'var', 'run', 'uwsgi.socket')
        app_module, _, app_var = appmod.rpartition('.')
        call = ['uwsgi', '--logdate', '--manage-script-name',  '--master', '--enable-threads',
                '--mount', f'/{args.subdir}={app_module}:{app_var}', '--daemonize', logfile, '--pidfile', pidfile,
                '--socket', socket, '--plugin', args.plugin, '--virtualenv', args.venv,
                '--ini', get_config('CONFIG')]
        if not socket.startswith('/'):
            call.extend(['--protocol', 'http'])
        res = subprocess.run(call)
        if res.returncode == 0:
            logger.info('UWSGI process started and daemonized')
        else:
            logger.info('UWSGI process start failed with return code %s', res.returncode)
            sys.exit(1)
    elif command == 'stop':
        res = subprocess.run(['uwsgi', '--stop', op.join(rootdir, 'var', 'run', 'uwsgi.pid')])
        if res.returncode == 0:
            logger.info('UWSGI process stopped')
        else:
            logger.info('UWSGI process stop failed with return code %s', res.returncode)
            sys.exit(1)


def setup_parser(parser):
    parser_sub = parser.add_subparsers(dest='command', help='UWSGI command')
    parser_sub.required = True
    parser_start = parser_sub.add_parser('start', help='Start UWSGI')
    parser_start.add_argument('-s', '--socket', help='Socket path')
    parser_start.add_argument('-d', '--subdir', default='', help='Subdirectory app mount')
    parser_start.add_argument('-p', '--plugin', default='python3', help='UWSGI plugin (default: python3)')
    parser_stop = parser_sub.add_parser('stop', help='Stop UWSGI')
    parser.set_defaults(call=cmd_uwsgi, use_venv=False)
