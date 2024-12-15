FROM python:3.11-slim-buster

WORKDIR /app

COPY webserver /app/webserver
COPY timer_queue /app/timer_queue

RUN pip install -r /app/webserver/requirements.txt
RUN pip install -r /app/timer_queue/requirements.txt

EXPOSE 8000

CMD ["uvicorn", "webserver.main:app", "--host", "0.0.0.0", "--port", "8000"]