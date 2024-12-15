#  Copyright (c) [2024] [Maksim Moiseenkov]
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Consumer microservice listens for messages from RabbitMQ and saves them in PostgreSQL database."""
import json
import logging
import os
from time import sleep

from db.client import (
    PostgresClient,
    PostgresClientException,
)
from timer_queue.client import RabbitMQClient
from timer_queue.exceptions import RabbitMqConnectionException

RABBIT_MQ_HOST = os.environ.get("RABBIT_MQ_HOST", "rabbitmq")
RABBIT_MQ_PORT = int(os.environ.get("RABBIT_MQ_PORT", "5672"))
RABBIT_MQ_INCOMING = os.environ.get("RABBIT_MQ_INCOMING", "unknown_incoming")
RABBIT_MQ_RECONNECTING_INTERVAL = int(os.environ.get("RABBIT_MQ_RECONNECTING_INTERVAL", "2"))
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD =os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")


SQL_CREATE_TIMERS_TABLE = """
CREATE TABLE IF NOT EXISTS timers (
    id UUID PRIMARY KEY,
    hours INTEGER,
    minutes INTEGER,
    seconds INTEGER,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    fire_at TIMESTAMP WITH TIME ZONE
)
"""
SQL_INSERT_TIMER = """
INSERT INTO timers (id, hours, minutes, seconds, url, created_at, fire_at)
VALUES ('{}', {}, {}, {}, '{}', '{}', '{}')
"""
SQL_CREATE_TIMERS_TO_FIRE_TABLE = """
CREATE TABLE IF NOT EXISTS timers_to_fire (
    id UUID PRIMARY KEY,
    fire_at TIMESTAMP WITH TIME ZONE,
    url TEXT
)
"""
SQL_INSERT_TIMER_TO_FIRE = """
INSERT INTO timers_to_fire (id, fire_at, url)
VALUES ('{}', '{}', '{}')
"""


logger = logging.getLogger(__name__)


def consume_messages():
    def callback(ch, method, properties, body):
        """Callback for saving incoming messages to database."""
        payload = json.loads(body.decode())
        db_client = PostgresClient(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        while True:
            logger.info("Attempting to save message to database")
            try:
                db_client.run_queries([
                    SQL_CREATE_TIMERS_TABLE,
                    SQL_INSERT_TIMER.format(
                        payload["id"],
                        payload["hours"],
                        payload["minutes"],
                        payload["seconds"],
                        payload["url"],
                        payload["created_at"],
                        payload["fire_at"]
                    ),
                    SQL_CREATE_TIMERS_TO_FIRE_TABLE,
                    SQL_INSERT_TIMER_TO_FIRE.format(payload["id"], payload["fire_at"], payload["url"]),
                ])
            except PostgresClientException as ex:
                logger.error("Error occurred while saving message to database: {}. Retry in 1 sec...".format(ex))
                sleep(1)
                continue
            else:
                return

    while True:
        queue_client = RabbitMQClient(host=RABBIT_MQ_HOST, port=RABBIT_MQ_PORT)
        try:
            queue_client.consume_messages(queue_name=RABBIT_MQ_INCOMING, call_back=callback)
        except KeyboardInterrupt:
            return
        except RabbitMqConnectionException as ex:
            logger.warning(
                "Connection error during the messages consumption. Details: %s. Reconnecting in %i sec.",
                str(ex),
                RABBIT_MQ_RECONNECTING_INTERVAL,
            )
            sleep(RABBIT_MQ_RECONNECTING_INTERVAL)


if __name__ == "__main__":
    consume_messages()
