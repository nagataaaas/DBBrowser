import glob
import os

import uvicorn

from config import DEBUG
from urls import app

if __name__ == '__main__':
    uvicorn.run(app=app, host="0.0.0.0")
