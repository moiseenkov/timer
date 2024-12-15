FROM python:3.11-slim-buster

WORKDIR /app

COPY trigger /app/trigger
COPY timer_queue /app/timer_queue

RUN pip install -r /app/trigger/requirements.txt
RUN pip install -r /app/timer_queue/requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "/app/trigger/main.py"]
