import sqlite3
from itertools import count
from uuid import uuid4
import os
import shutil

import time


class Environment:
    def __init__(self):
        self.session_id = uuid4().hex
        self.env = {'session_id': self.session_id, 'env': self}
        self.max_db = 0
        self.history = ''''''

        sample_file = './static/db/' + self.session_id + '.db'
        shutil.copy('./static/database.db', sample_file)
        conn = sqlite3.connect(sample_file)
        c = conn.cursor()
        self.env['sample_conn'], self.env['sample_c'] = conn, c
        self.env['sample_path'] = sample_file

    def add_db(self, filepath: str):
        for i in count(1):
            if 'conn{}'.format(i) in self.env:
                continue
            conn = sqlite3.connect(filepath)
            c = conn.cursor()
            data = ['conn{}'.format(i), 'c{}'.format(i), 'db{}_path'.format(i)]
            self.env[data[0]], self.env[data[1]] = conn, c
            self.env[data[2]] = filepath
            break
        self.max_db += 1
        return data

    def get_tables(self, cursor_name: str) -> None or list[str]:
        if not cursor_name or cursor_name not in self.env:
            return None
        cursor = self.env[cursor_name]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return list(cursor.fetchone())

    def get_columns(self, cursor_name: str, table_name: str) -> None or list[str]:
        if not cursor_name or not table_name or cursor_name not in self.env:
            return None
        cursor = self.env[cursor_name]
        try:
            cursor.execute('SELECT * FROM %s LIMIT 1' % table_name)
        except sqlite3.OperationalError:
            return None
        return list(map(lambda x: x[0], cursor.description))

    def __del__(self):
        self.env['sample_conn'].rollback()
        self.env['sample_c'].close()
        self.env['sample_conn'].close()
        time.sleep(0.3)
        os.remove(self.env['sample_path'])
        for i in range(1, self.max_db + 1):
            self.env['conn{}'.format(i)].rollback()
            self.env['c{}'.format(i)].close()
            self.env['conn{}'.format(i)].close()
            print(self.env['db{}_path'.format(i)])
            os.remove(self.env['db{}_path'.format(i)])
