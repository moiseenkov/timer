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

import os
import uuid
from pyexpat.errors import messages
from unittest import mock, expectedFailure

from sqlalchemy.testing import expect_deprecated

from db.client import PostgresClientException
from timer.main import select_timers_to_fire, schedule_hooks_firing
from timer_queue.exceptions import RabbitMqConnectionException

TEST_ID = str(uuid.uuid4())
TEST_URL = "http://example.com"
RABBIT_MQ_TO_FIRE = "timers_to_fire"
TIMER_PATH = "timer.main.{}"

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
SQL_DELETE_TIMERS_TO_FIRE = f"""
DELETE FROM timers_to_fire
WHERE id = '{TEST_ID}';
"""


class TestTimer:

    # def setup_method(self):
    #     ...

    def test_select_timers_to_fire(self):
        mock_db_client = mock.MagicMock()
        expected_result = mock.MagicMock()
        mock_result = [mock.MagicMock(), expected_result]
        mock_db_client.run_queries.return_value = mock_result

        result = select_timers_to_fire(mock_db_client)

        assert result == expected_result
        mock_db_client.run_queries.assert_called_once_with([
            SQL_CREATE_TIMERS_TO_FIRE_TABLE,
            SQL_SELECT_TIMERS_TO_FIRE,
        ])

    @mock.patch(TIMER_PATH.format("sleep"))
    @mock.patch(TIMER_PATH.format("logging"))
    def test_select_timers_to_fire_exception(self, mock_logging, mock_slip):
        mock_db_client = mock.MagicMock()
        expected_result = mock.MagicMock()
        mock_result = [mock.MagicMock(), expected_result]
        mock_db_client.run_queries.side_effect = [
            PostgresClientException,
            mock_result
        ]

        result = select_timers_to_fire(mock_db_client)

        assert result == expected_result
        mock_slip.assert_called_once_with(1)

    @mock.patch(TIMER_PATH.format("select_timers_to_fire"))
    @mock.patch(TIMER_PATH.format("RabbitMQClient"))
    @mock.patch(TIMER_PATH.format("PostgresClient"))
    @mock.patch(TIMER_PATH.format("sleep"))
    def test_schedule_hooks_firing(
            self,
            mock_sleep,
            mock_db_client,
            mock_rabbit_client,
            mock_select_timers_to_fire,
    ):
        mock_db = mock_db_client.return_value
        mock_mq = mock_rabbit_client.return_value
        expect_timer_timer = (TEST_ID, mock.MagicMock(), TEST_URL)
        expected_message = dict(id=TEST_ID, url=TEST_URL)
        mock_select_timers_to_fire.side_effect = [
            [expect_timer_timer],
            KeyboardInterrupt
        ]

        schedule_hooks_firing()

        mock_db_client.assert_called_once()
        mock_rabbit_client.assert_called_once()
        mock_sleep.assert_called_once_with(2)
        mock_mq.push_message.assert_called_once_with(queue_name=RABBIT_MQ_TO_FIRE, message=expected_message)
        mock_db.run_queries.assert_called_once_with([SQL_DELETE_TIMERS_TO_FIRE])

    @mock.patch(TIMER_PATH.format("select_timers_to_fire"))
    @mock.patch(TIMER_PATH.format("RabbitMQClient"))
    @mock.patch(TIMER_PATH.format("PostgresClient"))
    @mock.patch(TIMER_PATH.format("sleep"))
    def test_schedule_hooks_firing_no_timers(
        self,
        mock_sleep,
        mock_db_client,
        mock_rabbit_client,
        mock_select_timers_to_fire,
    ):
        mock_select_timers_to_fire.side_effect = [
            None,
            KeyboardInterrupt
        ]

        schedule_hooks_firing()

        mock_db_client.assert_called_once()
        mock_rabbit_client.assert_called_once()
        mock_sleep.assert_called_once_with(2)

    @mock.patch(TIMER_PATH.format("select_timers_to_fire"))
    @mock.patch(TIMER_PATH.format("RabbitMQClient"))
    @mock.patch(TIMER_PATH.format("PostgresClient"))
    @mock.patch(TIMER_PATH.format("sleep"))
    def test_schedule_hooks_firing_exception(
        self,
        mock_sleep,
        mock_db_client,
        mock_rabbit_client,
        mock_select_timers_to_fire,
    ):
        mock_db = mock_db_client.return_value
        mock_mq = mock_rabbit_client.return_value
        mock_mq.push_message.side_effect = [
            RabbitMqConnectionException,
            mock.MagicMock(),
        ]
        expect_timer_timer = (TEST_ID, mock.MagicMock(), TEST_URL)
        expected_message = dict(id=TEST_ID, url=TEST_URL)
        mock_select_timers_to_fire.side_effect = [
            [expect_timer_timer],
            KeyboardInterrupt
        ]

        schedule_hooks_firing()

        mock_db_client.assert_called_once()
        mock_rabbit_client.assert_called_once()
        mock_sleep.assert_called_once_with(2)
        mock_mq.push_message.assert_called_once_with(queue_name=RABBIT_MQ_TO_FIRE, message=expected_message)
        assert not mock_db.run_queries.called