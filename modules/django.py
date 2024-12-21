import importlib
import subprocess
import sys
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import argparse

from .. import logger


COMMANDS = {'admin': 'Django admin CLI utility', 'manage': 'Django manage.py utility',
            'run': 'Django development server'}


def cmd_admin(args: 'argparse.Namespace'):
    subprocess.run(['django-admin'] + args.arg)


def cmd_manage(args: list[str]):
    try:
        manager = importlib.import_module('manage')
    except ImportError:
        logger.error('Cannot import manage.py script, try "./ctl admin startproject <project-name> ." first')
        sys.exit(1)
    sys.argv = [manager.__file__ or 'manager.py'] + args
    manager.main()


def cmd_run(args: 'argparse.Namespace'):
    cmd_manage(['runserver'] + args.arg)


def setup_parser(cmd: str, parser: 'argparse.ArgumentParser'):
    if cmd == 'admin':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_admin)
    elif cmd == 'manage':
        def dfl(args: 'argparse.Namespace'):
            return cmd_manage(args.arg)

        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=dfl)
    elif cmd == 'run':
        parser.add_argument('arg', nargs='*')
        parser.set_defaults(call=cmd_run)
