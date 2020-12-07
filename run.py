from urls import app, env
import uvicorn

if __name__ == '__main__':
    try:
        uvicorn.run(app=app)
    except:
        for environ in env.values():
            del environ
