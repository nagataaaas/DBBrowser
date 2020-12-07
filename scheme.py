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


class EnvironmentNotFound(BaseModel):
    states: str = 'error'
    message: str = 'No environment found. Maybe timeout...?'
