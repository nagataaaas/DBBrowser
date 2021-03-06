import glob
import os

import uvicorn

from config import DEBUG
from urls import app

if __name__ == '__main__':
    if DEBUG:
        for file in glob.glob('static/db/*'):
            os.remove(file)
    os.makedirs('static/db', exist_ok=True)
    uvicorn.run(app=app, host="0.0.0.0")
