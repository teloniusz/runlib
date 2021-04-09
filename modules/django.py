import importlib
import subprocess
import sys

from .. import logger


COMMANDS = {'admin': 'Django admin CLI utility', 'manage': 'Django manage.py utility',
            'run': 'Django development server'}


def cmd_admin(args):
    subprocess.run(['django-admin'] + args.arg)


def cmd_manage(args):
    try:
        manager = importlib.import_module('manage')
    except ImportError:
        logger.error('Cannot import manage.py script, try "./ctl admin startproject <project-name> ." first')
        sys.exit(1)
    sys.argv = [manager.__file__] + args
    manager.main()


def cmd_run(args):
    cmd_manage(['runserver'] + args.arg)


def setup_parser(cmd, parser):
    if cmd == 'admin':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_admin)
    elif cmd == 'manage':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=lambda args: cmd_manage(args.arg))
    elif cmd == 'run':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_run)
