FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

ENV PYTHONBUFFERED 1

# install gcc
RUN apt-get update && apt-get install -y gcc python3-dev

RUN pip install --upgrade pip
ADD ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
ADD ./ /api
WORKDIR /api