import sqlite3
from itertools import count
from uuid import uuid4
import os
import shutil

import time

from scheme import *

from enum import Enum

from typing import List, Tuple
from pprint import pprint


class Environment:
    def __init__(self, new=True):
        self.session_id = uuid4().hex
        self.env = {'session_id': self.session_id, 'env': self, 'pprint': pprint}
        self.max_db = 0

        sample_file = './static/db/' + self.session_id + '.db'
        while new or not os.path.exists(sample_file) or not os.path.getsize(sample_file):
            shutil.copy('./static/database.db', sample_file)
            time.sleep(0.3)
            if os.path.getsize(sample_file):
                break

        conn = sqlite3.connect(sample_file)
        c = conn.cursor()
        self.env['sample_conn'], self.env['sample_c'] = conn, c
        self.env['sample_path'] = sample_file

        self.db_editor = None
        self.create_db_editor('sample_c')

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

    def get_tables(self, cursor_name: str) -> None or List[str]:
        if not cursor_name or cursor_name not in self.env:
            return None
        cursor = self.env[cursor_name]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return list(cursor.fetchone())

    def get_columns(self, cursor_name: str, table_name: str) -> None or List[str]:
        if not cursor_name or not table_name or cursor_name not in self.env:
            return None
        cursor = self.env[cursor_name]
        try:
            cursor.execute('SELECT * FROM %s LIMIT 1' % table_name)
        except sqlite3.OperationalError:
            return None
        return list(map(lambda x: x[0], cursor.description))

    def get_table_info(self, cursor_name: str, table_name: str, cursor: sqlite3.Cursor = None):

        if not cursor or not isinstance(cursor, sqlite3.Cursor):
            if not cursor_name in self.env:
                raise ValueError
            cursor = self.env[cursor_name]

            if not isinstance(cursor, sqlite3.Cursor):
                raise TypeError

        index_list = [data[1] for data in cursor.execute('PRAGMA index_list({});'.format(table_name)).fetchall()]
        indexed_list = {cursor.execute('pragma index_info({});'.format(col)).fetchone()[2] for col in index_list}
        table = DatabaseTableInfo()
        table.tableName = table_name

        cursor.execute("PRAGMA table_info('{}')".format(table_name))
        for col_info in cursor.fetchall():
            column = DatabaseColumnInfo()
            column.columnName = col_info[1]
            column.columnType = col_info[2]
            column.notNull = bool(col_info[3])
            column.default = col_info[4] or '<span class="null">null</span>'
            column.defaultRaw = col_info[4]
            column.primaryKey = bool(col_info[5])
            column.indexed = column.columnName in indexed_list

            table.columns.append(column)

        cursor.execute('SELECT COUNT(*) FROM {}'.format(table_name))
        table.rowCount = cursor.fetchone()[0]
        return table

    def get_db_info(self, cursor_name: str, cursor: sqlite3.Cursor = None) -> DatabaseInfo:
        if not cursor or not isinstance(cursor, sqlite3.Cursor):
            if cursor_name not in self.env:
                raise ValueError
            cursor = self.env[cursor_name]

            if not isinstance(cursor, sqlite3.Cursor):
                raise TypeError

        result = DatabaseInfo()

        table_names = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        table_names = [table[0] for table in table_names]

        for table_name in table_names:
            result.tables.append(self.get_table_info('', table_name, cursor))
        return result

    def create_db_editor(self, cursor_name: str):
        self.db_editor = DBEditor(self, cursor_name)
        self.env['db_editor'] = self.db_editor

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


class Operation(Enum):
    Equal = 0
    NotEqual = 1
    In = 2
    NotIn = 3
    Between = 4
    NotBetween = 5
    Like = 6
    Smaller = 7
    SmallerEq = 8
    Larger = 9
    LargerEq = 10


class CompOperation:
    integer_type = {'integer'}

    def __init__(self, db_editor: 'DBEditor', operation: Operation, value: List[str]):
        self.db_editor = db_editor
        self.operation = operation
        self.value = value
        if db_editor.column.columnType in self.integer_type:
            self.value = list(map(int, self.value))

    @property
    def sql(self):
        if self.operation == Operation.Equal:
            if self.value == [None]:
                return f'{self.db_editor.column.columnName} IS NULL'
            else:
                return f"{self.db_editor.column.columnName}={repr(self.value[0])}"
        elif self.operation == Operation.NotEqual:
            if self.value == [None]:
                return f'{self.db_editor.column.columnName} IS NOT NULL'
            else:
                return f"{self.db_editor.column.columnName} <> {repr(self.value[0])}"
        elif self.operation == Operation.In:
            if len(self.value) == 1:
                return f"{self.db_editor.column.columnName} IN ({repr(self.value[0])})"
            return f"{self.db_editor.column.columnName} IN {repr(tuple(self.value))}"
        elif self.operation == Operation.NotIn:
            return f"{self.db_editor.column.columnName} NOT IN {repr(tuple(self.value))}"
        elif self.operation == Operation.Between:
            return f"{self.db_editor.column.columnName} BETWEEN {self.value[0]} AND {self.value[1]}"
        elif self.operation == Operation.NotBetween:
            return f"{self.db_editor.column.columnName} NOT BETWEEN {self.value[0]} AND {self.value[1]}"
        elif self.operation == Operation.Like:
            return f"{self.db_editor.column.columnName} LIKE {repr(self.value[0])}"
        elif self.operation == Operation.Smaller:
            return f"{self.db_editor.column.columnName} < {repr(self.value[0])}"
        elif self.operation == Operation.SmallerEq:
            return f"{self.db_editor.column.columnName} <= {repr(self.value[0])}"
        elif self.operation == Operation.Larger:
            return f"{self.db_editor.column.columnName} > {repr(self.value[0])}"
        elif self.operation == Operation.LargerEq:
            return f"{self.db_editor.column.columnName} >= {repr(self.value[0])}"

    def __str__(self):
        return self.sql

    def and_(self, other: 'CompOperation'):
        return f'({self.sql}) AND ({other.sql})'

    def or_(self, other: 'CompOperation'):
        return f'({self.sql}) OR ({other.sql})'

    def xor_(self, other: 'CompOperation'):
        return f'({self.sql}) XOR ({other.sql})'


class TableSelector:
    def __init__(self, table: str, select: List[str] = None, clone=False):
        if clone:
            return
        self.table = table
        if select is None:
            select = []
        self.select_ = select
        self.condition = []
        self.limit_ = 0
        self.offset_ = 0
        self.order_by_: List[str] = []
        self.cursor: sqlite3.Cursor = None
        self.table_info: DatabaseTableInfo = None
        self.cols: List[str] = None

    def select(self, *items: 'DBEditor') -> 'TableSelector':
        this = self.clone()
        this.select_ = [val if isinstance(val, str) else val.column.columnName for val in items]
        return this

    def filter(self, *condition: CompOperation) -> 'TableSelector':
        this = self.clone()
        this.condition = condition
        return this

    def limit(self, limit_num: int = 1) -> 'TableSelector':
        this = self.clone()
        this.limit_ = limit_num
        return this

    def offset(self, offset_num: int = 0) -> 'TableSelector':
        this = self.clone()
        this.offset_ = offset_num
        return this

    def first(self) -> 'TableSelector':
        return self.limit(1)

    def order_by(self, *order: str) -> 'TableSelector':
        this = self.clone()
        this.order_by_ = order
        return this

    def clone(self):
        this = TableSelector(None, clone=True)
        this.table = self.table
        this.select_ = self.select_
        this.condition = self.condition
        this.limit_ = self.limit_
        this.offset_ = self.offset_
        this.order_by_ = self.order_by_
        this.cursor = self.cursor
        this.table_info = self.table
        this.cols = self.cols

        return this

    @property
    def select_query(self):
        select = 'SELECT ' + ('*' if not self.select_ else ', '.join(self.select_))
        from_ = f' FROM {self.table}'
        condition = ' WHERE ' + ' AND '.join(map(str, self.condition))
        limit = f' LIMIT {self.limit_}'
        offset = f' OFFSET {self.offset_}'
        order = []
        for od in self.order_by_:
            if isinstance(od, DBEditor):
                order.append(f'{od.columnName} {"ASC" if od.positive else "DESC"}')
            else:
                order.append(f'{od} ASC')
        order_by = f' ORDER BY {", ".join(order)}'

        query = select + from_
        if self.condition:
            query += condition
        if self.order_by_:
            query += order_by
        if self.limit_:
            query += limit
        if self.offset_:
            query += offset

        return query

    @property
    def delete_query(self):
        from_ = f'DELETE FROM {self.table}'
        condition = ' WHERE ' + ' AND '.join(map(str, self.condition))
        limit = f' LIMIT {self.limit_}'
        order = []
        for od in self.order_by_:
            if isinstance(od, DBEditor):
                order.append(f'{od.columnName} {"ASC" if od.positive else "DESC"}')
            else:
                order.append(f'{od} ASC')
        order_by = f' ORDER BY {", ".join(order)}'

        query = from_
        if self.condition:
            query += condition
        if self.order_by_:
            query += order_by
        if self.limit_:
            query += limit
        print(query)

        return query

    def insert_query(self, values):
        if isinstance(values, str):
            values = [values]
        if len(self.cols) != len(values):
            raise ValueError('Not matching length for selected values')
        return f'INSERT INTO {self.table} VALUES ({", ".join(repr(val) for val in values)})'

    def update_query(self, values):
        update = f'UPDATE {self.table}'
        if isinstance(values, str):
            values = [values]
        if len(values) != len(self.select_):
            print(values, self.select_)
            raise ValueError('Not matching length for selected values')
        set = f' SET ' + (', '.join(f'{key} = {repr(val)}' for key, val in zip(self.select_, values)))
        condition = ' WHERE ' + ' AND '.join(map(str, self.condition))
        limit = f' LIMIT {self.limit_}'
        order = []
        for od in self.order_by_:
            if isinstance(od, DBEditor):
                order.append(f'{od.columnName} {"ASC" if od.positive else "DESC"}')
            else:
                order.append(f'{od} ASC')
        order_by = f' ORDER BY {", ".join(order)}'

        query = update + set
        if self.condition:
            query += condition
        if self.order_by_:
            query += order_by
        if self.limit_:
            query += limit

        return query

    def delete(self):
        if self.cursor is None:
            raise ValueError('No cursor given')
        self.cursor.execute(self.delete_query)

    def insert(self, values):
        if self.cursor is None:
            raise ValueError('No cursor given')
        self.cursor.execute(self.insert_query(values))

    def get(self, query='') -> dict:
        if self.cursor is None:
            raise ValueError('No cursor given')
        if not self.select_:
            cols = self.cols
        else:
            cols = self.select_
        self.cursor.execute(query or self.select_query)
        result = self.cursor.fetchall()
        if self.limit_ == 1:
            return {k: v for k, v in zip(cols, result[0])}
        return [{k: v for k, v in zip(cols, row)} for row in result]

    def __setitem__(self, key, item):
        if self.cursor is None:
            raise ValueError('No cursor given')
        if not isinstance(key, (tuple, list)):
            key = [key]
        if not isinstance(item, (tuple, list)):
            item = [item]
        this = self.select(*key)
        this.cursor.execute(this.update_query(item))


class DBEditor:
    def __init__(self, environment: Environment, cursor_name: str, clone: bool = False):
        if clone:
            return
        assert cursor_name in environment.env
        cursor = environment.env[cursor_name]
        if not isinstance(cursor, sqlite3.Cursor):
            raise TypeError('not cursor object')
        self.env = environment
        self.cursor = cursor

        self.dbinfo = self.env.get_db_info('', self.cursor)
        self.columns = {
            table.tableName.lower().replace(' ', '_'): {col.columnName.lower().replace(' ', '_'): col for col in
                                                        table.columns} for table in self.dbinfo.tables}

        self.table = None
        self.column = None
        self.positive = True

    def clone(self) -> 'DBEditor':
        this = DBEditor(None, '', True)
        this.env = self.env
        this.cursor = self.cursor

        this.dbinfo = self.dbinfo
        this.columns = self.columns

        this.table = self.table
        this.column = self.column
        this.positive = self.positive

        return this

    def __getattr__(self, item) -> 'DBEditor':
        if self.table is None:
            if item in self.columns:
                new = self.clone()
                new.table = item
                return new
        if self.column is None:
            if item in self.columns[self.table]:
                new = self.clone()
                new.column = self.columns[self.table][item]
                return new
        if self.column is not None:
            if hasattr(self.column, item):
                return getattr(self.column, item)
        raise AttributeError('No attribute found: {}'.format(item))

    def __eq__(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.Equal, [other])

    def __ne__(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.NotEqual, [other])

    def in_(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.In, [*other])

    def not_in_(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.NotIn, [*other])

    def between(self, bottom, top):
        if isinstance(bottom, DBEditor) or isinstance(top, DBEditor):
            pass
        return CompOperation(self, Operation.Between, [bottom, top])

    def not_between(self, bottom, top):
        if isinstance(bottom, DBEditor) or isinstance(top, DBEditor):
            pass
        return CompOperation(self, Operation.NotBetween, [bottom, top])

    def like(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.Like, [other])

    def __lt__(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.Smaller, [other])

    def __le__(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.SmallerEq, [other])

    def __gt__(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.Larger, [other])

    def __ge__(self, other):
        if isinstance(other, DBEditor):
            pass
        return CompOperation(self, Operation.LargerEq, [other])

    def __neg__(self):
        this = self.clone()
        this.positive = not this.positive
        return this

    @property
    def query(self):
        selector = TableSelector(self.table)
        selector.cursor = self.cursor
        selector.cols = self.columns[self.table]
        return selector

    def __getitem__(self, item):
        selector = TableSelector(self.table)
        if not isinstance(item, (tuple, list)):
            item = [item]
        selector.condition = item
        selector.cursor = self.cursor
        selector.cols = self.columns[self.table]
        return selector
