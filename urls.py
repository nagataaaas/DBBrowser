import copy
import os
import shutil
import traceback
from functools import partial
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Form, UploadFile, File, Cookie
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from models import Environment, DBEditor
from scheme import *
from utils import reload_or_None
from utils import stdoutIO

app = FastAPI(
    title='Online Database Query Executor',
    description='This provides online environment to execute sql query and view database.',
    version='0.1 alpha'
)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
jinja_env = templates.env

endpoints: [str, partial] = {}

env: Dict[str, Environment] = {}


def update_endpoint():
    global endpoints
    endpoints = {
        'index': partial(app.url_path_for, name=index.__name__),
        'run_python': partial(app.url_path_for, name=run_python.__name__),
        'upload_db': partial(app.url_path_for, name=upload_db.__name__),
        'db_info': partial(app.url_path_for, name=db_info.__name__),
        'table_data': partial(app.url_path_for, name=table_data.__name__)
    }


@app.get('/')
async def index(req: Request, session_id: Optional[str] = Cookie(None, description='the session_id. '
                                                                                   'can continue environment '
                                                                                   'with existing session_id',
                                                                 alias='sessionId', )):
    if session_id and session_id in env:
        response = templates.TemplateResponse('index.html', {'endpoints': endpoints,
                                                             'request': req,
                                                             'is_new': 'false'})
        return response
    new_env = reload_or_None(sessionId=session_id) or Environment()

    env[new_env.session_id] = new_env
    response = templates.TemplateResponse('index.html', {'endpoints': endpoints, 'request': req,
                                                         'is_new': 'true'})
    response.set_cookie('sessionId', new_env.session_id)
    return response


@app.get('/reset')
async def reset(req: Request, session_id: Optional[str] = Cookie(None, description='the session_id. '
                                                                                   'can continue environment '
                                                                                   'with existing session_id',
                                                                 alias='sessionId', )):
    if session_id and session_id in env:
        env[session_id].__del__()
        del env[session_id]

    new_env = Environment()

    env[new_env.session_id] = new_env
    response = templates.TemplateResponse('index.html', {'endpoints': endpoints, 'request': req,
                                                         'is_new': 'true'})
    response.set_cookie('sessionId', new_env.session_id)
    return response


@app.post('/api/python/run', response_model=PythonResultSuccess,
          responses={
              404: {'model': EnvironmentNotFound,
                    'description': 'when the environment match to sessionId is not found.'},
              400: {'model': PythonResultFailed, 'description': 'when python raise the error while executing'},
              200: {'model': PythonResultSuccess, 'description': 'run python code and return result.'}
          })
async def run_python(sessionId: str = Form(..., description='The session id. stored in cookie'),
                     code: str = Form(..., description='The python code to be exexuted'),
                     executeType: str = Form(..., description='the type of execution. one of "exec" or "eval"',
                                             regex='(exec|eval)')):
    result = None
    if sessionId not in env:
        new_env = reload_or_None(sessionId=sessionId)
        if not new_env:
            return JSONResponse(jsonable_encoder(EnvironmentNotFound()), 404)
        env[new_env.session_id] = new_env

    if executeType == 'exec':
        try:
            with stdoutIO() as s:
                exec(code, env[sessionId].env)
                result = s.getvalue()
        except Exception as e:
            return JSONResponse(
                jsonable_encoder(PythonResultFailed(errorType=type(e).__name__, traceback=traceback.format_exc(),
                                                    result=s.getvalue())), 400)
    elif executeType == 'eval':
        try:
            result = repr(eval(code, env[sessionId].env))
        except Exception as e:
            return JSONResponse(
                jsonable_encoder(PythonResultFailed(errorType=type(e).__name__, traceback=traceback.format_exc())), 400)
    return JSONResponse(jsonable_encoder(PythonResultSuccess(result=result)))


@app.get('/api/health')
def health(req: Request):
    return {'health': 'ok'}


@app.post('/api/upload/db', response_model=DatabaseUploadResult,
          responses={
              404: {'model': EnvironmentNotFound,
                    'description': 'when the environment match to sessionId is not found.'},
              200: {'model': DatabaseUploadResult, 'description': 'uploaded file and loaded to environment.'}
          })
async def upload_db(sessionId: str = Form(..., description='The session id. stored in cookie'),
                    file: UploadFile = File(..., description='database file which can open with sqlite3 in python3')):
    if sessionId not in env:
        new_env = reload_or_None(sessionId=sessionId)
        if not new_env:
            return JSONResponse(jsonable_encoder(EnvironmentNotFound()), 404)
        env[new_env.session_id] = new_env

    db_dir = './static/db'
    extension = Path(file.filename).suffix or 'db'
    new_file_base = sessionId + uuid4().hex
    filepath = str(Path(os.path.join(db_dir, new_file_base)).with_suffix(extension))

    with open(filepath, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    conn, c, file_var = env[sessionId].add_db(filepath)
    return JSONResponse(jsonable_encoder(DatabaseUploadResult(connection=conn, cursor=c,
                                                              filepathVar=file_var, filepath=repr(filepath))))


@app.get('/api/db/info',
         responses={
             404: {'model': EnvironmentNotFound,
                   'description': 'when the environment match to sessionId is not found.'},
             400: {'model': CursorNotFound,
                   'description': 'when the cursor match to cursorName is not found.'},
             200: {'model': DatabaseUploadResult, 'description': 'uploaded file and loaded to environment.'}
         })
async def db_info(cursorName: str, sessionId: str = Cookie(None, description='the session_id. '
                                                                             'can continue environment '
                                                                             'with existing session_id',
                                                           alias='sessionId', )):
    if sessionId not in env:
        return JSONResponse(jsonable_encoder(EnvironmentNotFound()), 404)
    try:
        result = env[sessionId].get_db_info(cursorName)
    except (ValueError, TypeError):
        return JSONResponse(jsonable_encoder(CursorNotFound()), 400)

    return JSONResponse(jsonable_encoder(result))


@app.get('/table_data', responses={
    404: {'model': EnvironmentNotFound,
          'description': 'when the environment match to sessionId is not found.'},
    400: {'model': CursorNotFound,
          'description': 'when the cursor match to cursorName is not found.'},
    200: {'model': DatabaseColumnData, 'description': 'The data of database.'}
})
async def table_data(cursorName: str, tableName: str, offset: int, limit: int, sessionId: str, query: str,
                     python: bool):
    if sessionId not in env:
        return JSONResponse(jsonable_encoder(EnvironmentNotFound()), 404)
    try:
        result = DatabaseColumnData()
        editor = DBEditor(env[sessionId], cursorName).__getattr__(tableName)
        if query:
            if python:
                query_ = editor
                loc = copy.copy(env[sessionId].env)
                loc.update({k: query_.__getattr__(k) for k in editor.columns[tableName.lower()]})
                query_ = editor.__getitem__(eval(query, loc))
                result.data = list(query_.limit(limit).offset(offset).get())
            else:
                query_ = editor.query
                query_.condition = [query]
                result.data = list(query_.limit(limit).offset(offset).get())
        else:
            query_ = editor.query
            result.data = list(query_.limit(limit).offset(offset).get())
        for ind, dat in enumerate(result.data, offset + 1):
            dat['index'] = ind
        result.columns = ['index'] + list(
            DBEditor(env[sessionId], cursorName).__getattr__(tableName).query.limit(1).get().keys())
    except (ValueError, TypeError):
        raise
        return JSONResponse(jsonable_encoder(CursorNotFound()), 400)
    return JSONResponse(jsonable_encoder(result))


update_endpoint()
