import logging
from os import path as op
import sys
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import argparse

from .. import logger, get_config_str


COMMANDS = {'flask': 'Flask CLI utility', 'run': 'Flask dev server'}


def cmd_flask(args: list[str]):
    import flask

    sys.argv = [op.join(get_config_str('ROOTDIR'), get_config_str('VENV.DIR'), 'bin', 'flask')] + args
    flask.cli.main()


def cmd_run(args: 'argparse.Namespace'):
    if args.debug:
        logger.setLevel(logging.DEBUG)
    flask_args = ['run']
    if args.host:
        flask_args.extend(['-h', args.host])
    if args.port:
        flask_args.extend(['-p', args.port])
    cmd_flask(flask_args)


def setup_parser(cmd: str, parser: 'argparse.ArgumentParser'):
    if cmd == 'flask':
        def dfl(args: 'argparse.Namespace'):
            return cmd_flask(args.arg)

        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=dfl)
    elif cmd == 'run':
        parser.add_argument('--host', help='Server host')
        parser.add_argument('-p', '--port', help='Server port number')
        parser.add_argument('-d', '--debug', action='store_true', default=False, help='Debug mode')
        parser.set_defaults(call=cmd_run)
