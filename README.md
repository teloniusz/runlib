# Runlib

Python virtualenv/running configuration/deploy manager.

## Purpose

To have a single extendable tool for:
* virtualenv management (creation, adding, removing pip packages)
* app running
* app management
* installation (with versioning)

## Installation


1. Either:
* copy runlib to the root of your project or
* use it as a git submodule or
* symlink it to the root of your project

The last solution is not recommended, as when deploying your app to another directory
or remote server the symlink could become inaccessible. Runlib would issue a warning
when trying this, but won't stop you.

Example of using it as a submodule:

```
$ git submodule init
$ git submodule add https://github.com/teloniusz/runlib.git
```

2. Copy `ctl` script from `runlib/examples` directory to the root of your project
3. Create a `config.ini` in the root of your project and fill it using examples

## Example usage

For a new flask application:

```
$ cat config.ini
[MAIN]
MODULES = flask

[ENVIRONMENT]
FLASK_APP = app
FLASK_ENV = development
$ ./ctl env add flask
INFO:runlib:Not in venv, entering.
INFO:runlib:Virtual env not found, creating.
INFO:runlib:Calling command: env with args: add pkg: 'flask'
WARNING:runlib:Cannot read requirements file: [Errno 2] No such file or directory: '/home/antek/prog/rtest/requirements.txt'
Collecting flask
(...)
Installing collected packages: itsdangerous, click, Werkzeug, MarkupSafe, Jinja2, flask
Successfully installed Jinja2-2.11.3 MarkupSafe-1.1.1 Werkzeug-1.0.1 click-7.1.2 flask-1.1.2 itsdangerous-1.1.0
$ cat <<EOF > app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'yo'
EOF
$ $ ./ctl run
INFO:runlib:Not in venv, entering.
INFO:runlib:Calling command: run with args:
 * Serving Flask app "app" (lazy loading)
 * Environment: development
 * Debug mode: on
INFO:werkzeug: * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
INFO:werkzeug: * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 291-928-420
^C$ ./ctl install --relink my.server.com:/opt/myapp
...
```

