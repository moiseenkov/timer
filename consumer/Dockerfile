FROM python:3.11-slim-buster

WORKDIR /app

COPY consumer /app/consumer
COPY timer_queue /app/timer_queue
COPY db /app/db

RUN pip install -r /app/timer_queue/requirements.txt
RUN pip install -r /app/db/requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "/app/consumer/main.py"]
