from functools import partial

from fastapi import FastAPI, Response, Form, UploadFile, File, Cookie
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from uuid import uuid4
import traceback
from utils import stdoutIO
from fastapi.encoders import jsonable_encoder
from pathlib import Path

from scheme import *
import os
import shutil
from models import Environment

app = FastAPI(
    title='Online Database Query Executor',
    description='This provides online environment to execute sql query and view database.',
    version='0.1 alpha'
)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
jinja_env = templates.env

endpoints: [str, partial] = {}

env: dict[str, Environment] = {}


def update_endpoint():
    global endpoints
    endpoints = {
        'index': partial(app.url_path_for, name=index.__name__),
        'run_python': partial(app.url_path_for, name=run_python.__name__),
        'upload_db': partial(app.url_path_for, name=upload_db.__name__)
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
    new_env = Environment()

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
        return JSONResponse(jsonable_encoder(EnvironmentNotFound), 404)
    env[sessionId].history = code
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


@app.post('/api/upload/db', response_model=DatabaseUploadResult)
async def upload_db(sessionId: str = Form(..., description='The session id. stored in cookie'),
                    file: UploadFile = File(..., description='database file which can open with sqlite3 in python3')):
    db_dir = './static/db'
    extension = Path(file.filename).suffix or 'db'
    new_file_base = sessionId + uuid4().hex
    filepath = str(Path(os.path.join(db_dir, new_file_base)).with_suffix(extension))

    with open(filepath, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    conn, c, file_var = env[sessionId].add_db(filepath)
    return JSONResponse(jsonable_encoder(DatabaseUploadResult(connection=conn, cursor=c,
                                                              filepathVar=file_var, filepath=repr(filepath))))


update_endpoint()
