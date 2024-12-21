import os
from os import path as op
import subprocess
import sys
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import argparse

from .. import get_config_str, logger


COMMANDS = {'uwsgi': 'UWSGI command'}


def cmd_uwsgi(args: 'argparse.Namespace'):
    rootdir = get_config_str('ROOTDIR')

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
        call = ['uwsgi', '--logdate', '--manage-script-name',  '--master', '--enable-threads',
                '--daemonize', logfile, '--pidfile', pidfile,
                '--socket', socket, '--plugin', args.plugin, '--virtualenv', args.venv,
                '--ini', get_config_str('CONFIG')]
        if args.app:
            call.extend(['--mount', args.app])
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


def setup_parser(cmd: str, parser: 'argparse.ArgumentParser'):
    parser_sub = parser.add_subparsers(dest='command', help='UWSGI operation')
    parser_sub.required = True
    parser_start = parser_sub.add_parser('start', help='Start UWSGI')
    parser_start.add_argument('-s', '--socket', help='Socket path')
    parser_start.add_argument('-a', '--app', default='/=app:app', help='App mount')
    parser_start.add_argument('-p', '--plugin', default='python3', help='UWSGI plugin (default: python3)')
    parser_sub.add_parser('stop', help='Stop UWSGI')
    parser.set_defaults(call=cmd_uwsgi, use_venv=False)
