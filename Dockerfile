FROM python:3.12

WORKDIR /code

RUN mkdir -p /code/log/

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80", "--log-config", "/code/app/logging.yml"]
