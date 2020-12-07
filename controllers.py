from functools import partial

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from fastapi.responses import HTMLResponse

from uuid import uuid4

from utils import stdoutIO

app = FastAPI(
    title='Online Database Query Executor',
    description='This provides online environment to execute sql query and view database.',
    version='0.1 alpha'
)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
jinja_env = templates.env

endpoints = {}

env = {}


def update_endpoint():
    global endpoints
    endpoints = {
        'index': partial(app.url_path_for, name=index.__name__)(),
        'run_python': partial(app.url_path_for, name=run_python.__name__)
    }


def health(req: Request):
    return {'health': 'ok'}


def index(req: Request):
    uuid = uuid4().hex
    env[uuid] = {'session_id': uuid}
    response = HTMLResponse(templates.TemplateResponse('index.html', {'endpoints': endpoints}))
    response.set_cookie('sessionId', uuid)
    return response


def run_python(req: Request):
    print(req)
    # with stdoutIO() as s:
    #     exec()
    return {'result': 1}

update_endpoint()