import sqlite3
from itertools import count
from uuid import uuid4
import os


class Environment:
    def __init__(self):
        self.session_id = uuid4().hex
        self.env = {'session_id': self.session_id}
        self.max_db = 0

    def add_db(self, filepath: str):
        for i in count(1):
            if 'conn{}'.format(i) in self.env:
                continue
            conn = sqlite3.connect(filepath)
            c = conn.cursor()
            self.env['conn{}'.format(i)], self.env['c{}'.format(i)] = conn, c
            self.env['db{}_path'] = filepath
            break
        self.max_db += 1

    def __del__(self):
        for i in range(1, self.max_db + 1):
            self.env['conn{}'.format(i)].rollback()
            self.env['conn{}'.format(i)].close()
            os.remove(self.env['db{}_path'])
