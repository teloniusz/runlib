import argparse
import importlib
import logging
from os import path as op

from . import get_config, logger, MODULES
from .modules import env


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

    for module in MODULES:
        try:
            mod = importlib.import_module(f'..{module}', __name__)
        except ImportError:
            try:
                mod = importlib.import_module(f'..modules.{module}', __name__)
            except ImportError as exc:
                logger.error('Error loading module %s: %s', module, str(exc))
                continue
        if hasattr(mod, 'COMMANDS') and hasattr(mod, 'setup_parser'):
            for cmd, help_str in mod.COMMANDS.items():
                mod.setup_parser(cmd, subparsers.add_parser(cmd, help=help_str))

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
