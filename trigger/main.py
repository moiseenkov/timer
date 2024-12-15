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

import json
import logging
import os
from time import sleep

import requests

from timer_queue.client import RabbitMQClient
from timer_queue.exceptions import RabbitMqConnectionException

RABBIT_MQ_HOST = os.environ.get("RABBIT_MQ_HOST", "rabbitmq")
RABBIT_MQ_PORT = int(os.environ.get("RABBIT_MQ_PORT", "5672"))
RABBIT_MQ_TO_FIRE = os.environ.get("RABBIT_MQ_TO_FIRE", "unknown_incoming")
RABBIT_MQ_RECONNECTING_INTERVAL = int(os.environ.get("RABBIT_MQ_RECONNECTING_INTERVAL", "2"))


logger = logging.getLogger(__name__)



def fire_hooks():
    """Callback for saving incoming messages to database."""
    def callback(ch, method, properties, body):
        logger.info("Received %r" % body)
        body = json.loads(body.decode())
        response = requests.post(url=body["url"], json={"id": body["id"]})
        logger.info(f"Firing hook {body}. Response status code: {response.status_code}")

    while True:
        queue_client = RabbitMQClient(host=RABBIT_MQ_HOST, port=RABBIT_MQ_PORT)
        try:
            queue_client.consume_messages(queue_name=RABBIT_MQ_TO_FIRE, call_back=callback)
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
    fire_hooks()