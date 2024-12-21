from os import path as op
import subprocess
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import argparse

from .. import get_config_str


COMMANDS = {'celery': 'Celery ops'}


def cmd_celery(args: 'argparse.Namespace'):
    here = get_config_str('ROOTDIR')
    objname = get_config_str('CELERY.OBJECT', 'app.celery')
    use_beat = get_config_str('CELERY.BEAT', 'y').strip().lower() in ('1', 'y', 'yes', 'true')

    piddir = op.join(here, 'var', 'run')
    logdir = op.join(here, 'var', 'log')
    pidfiles = {'worker': op.join(piddir, 'celery-worker.pid'), 'beat': op.join(logdir, 'celery-beat.pid')}
    logfiles = {'worker': op.join(logdir, 'celery-worker.log'), 'beat': op.join(logdir, 'celery-beat.log')}
    if args.operation == 'start':
        subprocess.check_call([
            'celery', '-A', objname, 'multi', 'start', 'worker',
            f'--loglevel={args.loglevel}', f'--pidfile={pidfiles["worker"]}', f'--logfile={logfiles["worker"]}'])
        if use_beat:
            subprocess.check_call([
                'celery', '-A', objname, 'beat',
                f'--loglevel={args.loglevel}', f'--pidfile={pidfiles["beat"]}', f'--logfile={logfiles["beat"]}',
                '--max-interval', '30', '-s', f'{op.join(piddir, "celery-beat")}', '--detach'])
    else:
        if use_beat:
            subprocess.check_call(['pkill', '-F', pidfiles["beat"]])
        subprocess.check_call([
            'celery', '-A', objname, 'multi', 'stop', 'worker',
            f'--pidfile={pidfiles["worker"]}', f'--logfile={logfiles["worker"]}'])


def setup_parser(cmd: str, parser: 'argparse.ArgumentParser'):
    parser.add_argument('operation', choices=('start', 'stop'))
    parser.set_defaults(call=cmd_celery)
