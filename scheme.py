from pydantic import BaseModel
from typing import List, Dict, Optional


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


class DatabaseUploadResult(BaseModel):
    connection: str = 'the variable name of connection to db'
    cursor: str = 'the variable name of cursor of connection'
    filepathVar: str = 'the variable name of uploaded db\'s filepath'
    filepath: str = 'the filepath of uploaded db'
