import configparser
import logging
import os
from os import path as op
import re
import sys


CONFIG = configparser.ConfigParser()
CONFIG.optionxform = lambda optionstr: str(optionstr)
MODULES = ['env', 'install']


def get_config(name: str, default: str = ''):
    if not CONFIG.has_section('MAIN'):
        raise AttributeError('Runlib not initialized. Please put runlib.init(__name__, ...) in the code')
    section, _, name = name.rpartition('.')
    if not section:
        section = 'MAIN'
    if not name:
        return CONFIG[section] if CONFIG.has_section(section) else (default or dict[str, str]())
    return CONFIG.get(section, name, fallback=default)


def get_config_str(name: str, default: str = ''):
    res = get_config(name, default)
    return res if isinstance(res, str) else default


def get_config_dict(name: str) -> dict[str, str]:
    res = get_config(name)
    return res if isinstance(res, dict) else {}


def load_config(filename: str, init: dict[str, str] | None = None):
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


def init(parent_module: str = '__main__', env: dict[str, str] | None = None, config: str = 'config.ini'):
    parent = sys.modules[parent_module]
    initial = {
        'APPNAME': getattr(parent, 'APPNAME', ''),
        'CONFIG': config,
        'ROOTDIR': op.realpath(op.dirname(getattr(parent, '__file__', './.'))),
        'VENV.DIR': '.venv',
        'VENV.REQUIREMENTS': 'requirements.txt',
    }
    cfg = load_config(op.join(initial['ROOTDIR'], config), initial)
    MODULES.extend(
        elem
        for elem in re.split('[ ,]+', get_config_str('MODULES'))
        if elem)

    try:
        environ = cfg['ENVIRONMENT']
    except KeyError:
        environ = dict[str, str]()
    environ.update(env or {})
    os.environ['ROOTDIR'] = cfg['MAIN']['ROOTDIR']
    for var, val in environ.items():
        val = op.expandvars(val)
        if var.endswith('!'):
            os.environ[var[0:-1]] = val
        elif not os.environ.get(var):
            os.environ[var] = val
    logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


from .base import get_parser, main

__all__ = ['get_parser', 'main', 'init', 'load_config', 'get_config', 'CONFIG', 'MODULES']