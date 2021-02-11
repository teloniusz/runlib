import argparse
import importlib
import logging
from os import path as op

from . import get_config, logger, env, uwsgi, install


APP = None


def get_app():
    global APP

    appmod = get_config('APPMOD')
    if APP is None:
        if '.' in appmod:
            module, _, app = appmod.rpartition('.')
            APP = getattr(importlib.import_module(module), app)
    return APP


def cmd_run(args):
    get_app().run(args.host, args.port, debug=args.debug)


def get_parser():
    rootdir = get_config('ROOTDIR')

    parser = argparse.ArgumentParser(description=get_config('APPNAME'))
    parser.set_defaults(use_venv=True)
    parser.add_argument('-l', '--loglevel',
                        choices=('ERROR', 'WARNING', 'NOTICE', 'INFO', 'DEBUG'),
                        default='INFO', help='Logging level')
    parser.add_argument('--venv', default=op.join(rootdir, get_config('VENV.DIR')),
                        help='alternative virtualenv location')

    subparsers = parser.add_subparsers(dest='cmd', help='command')
    subparsers.required = True

    parser_run = subparsers.add_parser('run', help='Run a test server')
    parser_run.add_argument('--host', help='Server host')
    parser_run.add_argument('-p', '--port', help='Server port number')
    parser_run.add_argument('-d', '--debug', action='store_true', default=False, help='Debug mode')
    parser_run.set_defaults(call=cmd_run)

    env.setup_parser(subparsers.add_parser('env', help='Virtualenv management'))
    uwsgi.setup_parser(subparsers.add_parser('uwsgi', help='UWSGI control'))
    install.setup_parser(subparsers.add_parser('install', help='Install app'))

    return parser, subparsers


def main(parser=None, before=None):
    def show_arg(arg, val):
        if arg == 'command':
            return val
        elif arg == 'arg':
            return f'''"{'" "'.join(val)}"'''
        return f'{arg}: {val!r}'

    if not parser:
        parser = get_parser()[0]
    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.loglevel))
    if args.use_venv:
        env.ensure_venv(args.venv)
    if before:
        before(args)
    logger.info('Calling command: %s with args: %s', args.cmd,
                ' '.join(show_arg(arg, val)
                         for arg, val in vars(args).items()
                         if val and arg not in ('call', 'cmd', 'venv', 'loglevel', 'use_venv')))
    args.call(args)
