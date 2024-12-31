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
import logging
import os
from time import sleep
from typing import Any

from db.client import PostgresClient, PostgresClientException
from timer_queue.client import RabbitMQClient
from timer_queue.exceptions import RabbitMqConnectionException

RABBIT_MQ_HOST = os.environ.get("RABBIT_MQ_HOST", "rabbitmq")
RABBIT_MQ_PORT = int(os.environ.get("RABBIT_MQ_PORT", "5672"))
RABBIT_MQ_TO_FIRE = os.environ.get("RABBIT_MQ_TO_FIRE", "timers_to_fire")
RABBIT_MQ_RECONNECTING_INTERVAL = int(os.environ.get("RABBIT_MQ_RECONNECTING_INTERVAL", "2"))
TIMER_DB_HOST = os.environ.get("TIMER_DB_HOST", "postgres")
TIMER_DB_PORT = int(os.environ.get("TIMER_DB_PORT", "5432"))
TIMER_DB_USER = os.environ.get("TIMER_DB_USER", "postgres")
TIMER_DB_PASSWORD =os.environ.get("TIMER_DB_PASSWORD", "postgres")
TIMER_DB_DB = os.environ.get("TIMER_DB_DB", "postgres")

SQL_CREATE_TIMERS_TO_FIRE_TABLE = """
CREATE TABLE IF NOT EXISTS timers_to_fire (
    id UUID PRIMARY KEY,
    fire_at TIMESTAMP WITH TIME ZONE,
    url TEXT
)
"""
SQL_SELECT_TIMERS_TO_FIRE = """
SELECT * 
FROM timers_to_fire
WHERE fire_at <= NOW() AT TIME ZONE 'UTC'
"""
SQL_DELETE_TIMERS_TO_FIRE = """
DELETE FROM timers_to_fire
WHERE id = '{}';
"""

logger = logging.getLogger(__name__)


def select_timers_to_fire(db_client: PostgresClient) -> list[Any]:
    """Selects timers from database that are ready to be fired."""
    timers_to_fire = []
    while True:
        try:
            results = db_client.run_queries([
                SQL_CREATE_TIMERS_TO_FIRE_TABLE,
                SQL_SELECT_TIMERS_TO_FIRE,
            ])
        except PostgresClientException as ex:
            logger.warning("Error occurred while fetching timers from database: %s. Retry in 1 sec.", ex)
            sleep(1)
            continue
        else:
            timers_to_fire = results[1]
            break
    return timers_to_fire


def schedule_hooks_firing():
    """Callback for saving incoming messages to database."""
    db_client = PostgresClient(
        host=TIMER_DB_HOST,
        port=TIMER_DB_PORT,
        database=TIMER_DB_DB,
        user=TIMER_DB_USER,
        password=TIMER_DB_PASSWORD
    )
    rabbitmq_client = RabbitMQClient(host=RABBIT_MQ_HOST, port=RABBIT_MQ_PORT)
    while True:
        try:
            if timers_to_fire := select_timers_to_fire(db_client=db_client):
                for timer in timers_to_fire:
                    logger.info(f"Found timer ready to fire!")
                    data = dict(zip(["id", "fire_at", "url"], timer))
                    message = {"id": str(data["id"]), "url": data["url"]}
                    try:
                        rabbitmq_client.push_message(queue_name=RABBIT_MQ_TO_FIRE, message=message)
                    except RabbitMqConnectionException as ex:
                        logger.error(
                            "Failed to push message to RabbitMQ for id %s due to error %s",
                            message["id"],
                            str(ex),
                        )
                        continue
                    else:
                        db_client.run_queries([SQL_DELETE_TIMERS_TO_FIRE.format(message["id"])])

            sleep(RABBIT_MQ_RECONNECTING_INTERVAL)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    schedule_hooks_firing()
