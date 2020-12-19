from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class PythonResultSuccess(BaseModel):
    states: str = 'success'
    message: str = 'Run successfully'
    result: str = 'result'


class PythonResultFailed(BaseModel):
    states: str = 'error'
    message: str = 'Failed to execute'
    errorType: str = 'type of error'
    traceback: str = 'python traceback'
    result: str = 'result (maybe until the line the error occurred)'


class EnvironmentNotFound(BaseModel):
    states: str = 'error'
    message: str = 'No environment found. Maybe timeout...?'


class CursorNotFound(BaseModel):
    states: str = 'error'
    message: str = 'No cursor. Maybe typo...?'


class DatabaseUploadResult(BaseModel):
    connection: str = 'the variable name of connection to db'
    cursor: str = 'the variable name of cursor of connection'
    filepathVar: str = 'the variable name of uploaded db\'s filepath'
    filepath: str = 'the filepath of uploaded db'


class DatabaseColumnInfo(BaseModel):
    columnName: str = 'the name of column'
    columnType: str = 'the type of column'
    notNull: bool = 0
    default: Any = 0
    defaultRaw: Any = 0
    primaryKey: bool = 0
    indexed: bool = 0


class DatabaseTableInfo(BaseModel):
    columns: List[DatabaseColumnInfo] = []
    rowCount: int = 0
    tableName: str = 'the name of table'


class DatabaseInfo(BaseModel):
    tables: List[DatabaseTableInfo] = []

class DatabaseColumnData(BaseModel):
    columns: List[str] = []
    data: List[Dict[str, str]] = []