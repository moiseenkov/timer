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
"""Helper class for interacting with RabbitMQ"""
import json
import logging
from typing import Any, Mapping, Callable

import pika
from pika.adapters.blocking_connection import (
    BlockingChannel,
    BlockingConnection,
)
from pika.delivery_mode import DeliveryMode
from pika.exceptions import AMQPConnectionError
from tenacity import retry, wait_exponential

from timer_queue.exceptions import RabbitMqConnectionException

logger = logging.getLogger(__name__)


class RabbitMQChannel:
    """Context manager for rabbitmq channel"""
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connection: BlockingConnection

    def __enter__(self) -> BlockingChannel:
        logger.info("Connecting to RabbitMQ on %s:%d ...", self.host, self.port)
        self.connection = BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port))
        channel = self.connection.channel()
        logger.info("Connected to RabbitMQ on %s:%d successfully", self.host, self.port)
        return channel

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.connection.close()
        logger.info("Closed connection to RabbitMQ on %s:%d successfully", self.host, self.port)


class RabbitMQClient:
    """Helper class for interaction with RabbitMQ"""
    def __init__(self, host: str, port: int = 5672) -> None:
        self.host = host
        self.port = port

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10))
    def push_message(self, queue_name: str, message: Mapping[str, Any]) -> None:
        """Push given message into a given RabbitMQ queue"""
        try:
            with RabbitMQChannel(host=self.host, port=self.port) as channel:
                logger.info("Attempting to push message to queue: %s", queue_name)
                channel.queue_declare(queue=queue_name, durable=True)
                channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=DeliveryMode.Persistent),
                )
        except AMQPConnectionError as ex:
            raise RabbitMqConnectionException(ex)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10))
    def consume_messages(self, queue_name: str, call_back: Callable) -> None:
        """Pull messages from a given RabbitMQ queue and process them by a given callback"""
        try:
            with RabbitMQChannel(host=self.host, port=self.port) as channel:
                logger.info("Start consuming messages from queue: %s", queue_name)
                channel.queue_declare(queue=queue_name, durable=True)
                channel.basic_consume(queue=queue_name, on_message_callback=call_back, auto_ack=True)
                channel.start_consuming()
        except AMQPConnectionError as ex:
            raise RabbitMqConnectionException(ex)
