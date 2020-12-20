import contextlib
import sys
from io import StringIO
import os
import glob
import sqlite3
from models import Environment


@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


def reload_or_None(sessionId):
    db_dir = './static/db'
    if not sessionId:
        return
    glob_data = glob.glob(os.path.join(db_dir, sessionId + '*'))
    if not glob_data:
        return
    new_env = Environment(new=False)
    new_env.session_id = sessionId
    i = 1
    for db in glob_data:
        if len(os.path.basename(db)) > 40:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            data = ['conn{}'.format(i), 'c{}'.format(i), 'db{}_path'.format(i)]
            new_env.env[data[0]], new_env.env[data[1]] = conn, c
            new_env.env[data[2]] = db

            i += 1
    return new_env


def remove_shallow_traceback(traceback_str: str):
    errors = traceback_str.split('\n')
    return '\n'.join(errors[:1] + errors[3:])