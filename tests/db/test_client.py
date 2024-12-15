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

from unittest import mock

import psycopg2
import pytest

from db.client import PostgresClient, PostgresClientException

TEST_HOST = 'test-host'
TEST_PORT = 80
TEST_DATABASE = 'test-database'
TEST_USER = 'test-user'
TEST_PASSWORD = 'test-password'
TEST_QUERY = "test-query"
EXPECTED_RESULT = mock.MagicMock()
TEST_QUERY_CREATE = """
CREATE TABLE employees (
    id INT PRIMARY KEY,
    name VARCHAR(255),
    department VARCHAR(255),
    salary DECIMAL(10, 2)
);
"""
TEST_QUERY_ALTER = """
ALTER TABLE employees
ADD COLUMN hire_date DATE;
"""
TEST_QUERY_DROP = "DROP TABLE salary;"
TEST_QUERY_TRUNCATE = "TRUNCATE TABLE employees;"
TEST_QUERY_SELECT = "SELECT * FROM employees;"
CLIENT_PATH = "db.client.{}"

class TestPostgresClient:
    def setup_method(self):
        self.client = PostgresClient(
            host=TEST_HOST,
            port=TEST_PORT,
            database=TEST_DATABASE,
            user=TEST_USER,
            password=TEST_PASSWORD,
        )

    @mock.patch(CLIENT_PATH.format("psycopg2.connect"))
    def test_connection(self, mock_connect):
        expected_connection = mock_connect.return_value

        connection = self.client.connection

        assert expected_connection == connection
        mock_connect.assert_called_once_with(
            host=TEST_HOST,
            port=TEST_PORT,
            database=TEST_DATABASE,
            user=TEST_USER,
            password=TEST_PASSWORD,
        )

    @mock.patch(CLIENT_PATH.format("psycopg2.connect"))
    def test_connection_exception(self, mock_connect):
        mock_connect.side_effect = psycopg2.Error

        with pytest.raises(PostgresClientException):
            _ = self.client.connection

        mock_connect.assert_called_once_with(
            host=TEST_HOST,
            port=TEST_PORT,
            database=TEST_DATABASE,
            user=TEST_USER,
            password=TEST_PASSWORD,
        )

    @pytest.mark.parametrize(
        "query, is_ddl, fetch_result, expected_results",
        [
            (TEST_QUERY, True, None, [None]),
            (TEST_QUERY, False, EXPECTED_RESULT, [EXPECTED_RESULT]),
        ]
    )
    @mock.patch(CLIENT_PATH.format("PostgresClient.is_dql_query"))
    @mock.patch(CLIENT_PATH.format("PostgresClient.is_ddl_query"))
    @mock.patch(CLIENT_PATH.format("psycopg2.connect"))
    def test_run_queries(
        self,
        mock_connect,
        mock_is_ddl_query,
        mock_is_dql_query,
        query,
        is_ddl,
        fetch_result,
        expected_results,
    ):
        mock_is_ddl_query.return_value = is_ddl
        mock_is_dql_query.return_value = not is_ddl
        commits_count = 2 if is_ddl else 1
        mock_cursor = mock_connect.return_value.cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = fetch_result

        results = self.client.run_queries([query])

        assert expected_results == results
        mock_connect.return_value.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(query)
        mock_is_ddl_query.assert_called_once_with(query)
        mock_is_dql_query.assert_called_once_with(query)

        assert mock_connect.return_value.commit.call_count == commits_count
        if not is_ddl:
            mock_cursor.fetchall.assert_called_once()

    @mock.patch(CLIENT_PATH.format("psycopg2.connect"))
    def test_run_queries_exception(self, mock_connect):
        mock_execute = mock_connect.return_value.cursor.return_value.__enter__.return_value.execute
        mock_execute.side_effect = psycopg2.Error

        with pytest.raises(PostgresClientException):
            self.client.run_queries([TEST_QUERY])

        mock_execute.assert_called_once_with(TEST_QUERY)

    @pytest.mark.parametrize(
        "query, expected_value",
        [
            (TEST_QUERY_CREATE, True),
            (TEST_QUERY_ALTER, True),
            (TEST_QUERY_DROP, True),
            (TEST_QUERY_TRUNCATE, True),
            (TEST_QUERY_SELECT, False),

        ]
    )
    def test_is_ddl_query(self, query, expected_value):
        result = self.client.is_ddl_query(query)
        assert result == expected_value

    @pytest.mark.parametrize(
        "query, expected_value",
        [
            (TEST_QUERY_CREATE, False),
            (TEST_QUERY_ALTER, False),
            (TEST_QUERY_DROP, False),
            (TEST_QUERY_TRUNCATE, False),
            (TEST_QUERY_SELECT, True),

        ]
    )
    def test_is_dql_query(self, query, expected_value):
        result = self.client.is_dql_query(query)
        assert result == expected_value
