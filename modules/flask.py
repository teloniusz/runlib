import logging
from os import path as op
import sys

from .. import logger, get_config


COMMANDS = {'flask': 'Flask CLI utility', 'run': 'Flask dev server'}


def cmd_flask(args):
    import flask

    sys.argv = [op.join(get_config('ROOTDIR'), get_config('VENV.DIR'), 'bin', 'flask')] + args
    flask.cli.main()


def cmd_run(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)
    flask_args = ['run']
    if args.host:
        flask_args.extend(['-h', args.host])
    if args.port:
        flask_args.extend(['-p', args.port])
    cmd_flask(flask_args)


def setup_parser(cmd, parser):
    if cmd == 'flask':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=lambda args: cmd_flask(args.arg))
    elif cmd == 'run':
        parser.add_argument('--host', help='Server host')
        parser.add_argument('-p', '--port', help='Server port number')
        parser.add_argument('-d', '--debug', action='store_true', default=False, help='Debug mode')
        parser.set_defaults(call=cmd_run)
