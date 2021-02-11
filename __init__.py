import configparser
import logging
import os
from os import path as op
import sys


CONFIG = configparser.ConfigParser()
CONFIG.optionxform = str


def get_config(name, default=''):
    if not CONFIG.has_section('MAIN'):
        raise AttributeError('Runlib not initialized. Please put runlib.init(__name__, ...) in the code')
    section, _, name = name.rpartition('.')
    if not section:
        section = 'MAIN'
    if not name:
        return CONFIG[section] if CONFIG.has_section(section) else (default or {})
    return CONFIG.get(section, name, fallback=default)


def load_config(filename, init=None):
    global CONFIG

    if init:
        for name, val in init.items():
            section, _, name = name.rpartition('.')
            try:
                CONFIG[section or 'MAIN'][name] = val
            except KeyError:
                CONFIG[section or 'MAIN'] = {name: val}
    CONFIG.read(filename)
    return CONFIG


def init(parent_module, appmod='app.app', env=None, config='config.ini'):
    parent = sys.modules[parent_module]
    initial = {
        'APPMOD': appmod,
        'APPNAME': getattr(parent, 'APPNAME', ''),
        'CONFIG': config,
        'ROOTDIR': op.realpath(op.dirname(getattr(parent, '__file__', './.'))),
        'VENV.DIR': '.venv',
        'VENV.REQUIREMENTS': 'requirements.txt'
    }
    config = load_config(op.join(initial['ROOTDIR'], config), initial)

    try:
        environ = config['ENVIRONMENT']
    except KeyError:
        environ = {}
    environ.update(env or {})
    os.environ['ROOTDIR'] = config['MAIN']['ROOTDIR']
    for var, val in environ.items():
        val = op.expandvars(val)
        if var.endswith('!'):
            os.environ[var[0:-1]] = val
        elif not os.environ.get(var):
            os.environ[var] = val
    logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


from .base import get_parser, main
