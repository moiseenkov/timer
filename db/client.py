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
"""Helper class for interacting with PostgreSQL"""
import logging
from functools import cached_property
from typing import Sequence, Any

import psycopg2

logger = logging.getLogger(__name__)


class PostgresClientException(Exception): ...


class PostgresClient:
    """Helper class for interacting with PostgreSQL."""
    def __init__(self, host: str, port: int, database: str, user: str, password: str) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    @cached_property
    def connection(self) -> psycopg2.extensions.connection:
        """Create connection to PostgreSQL."""
        try:
            logger.info("Connecting to PostgreSQL on {}:{}".format(self.host, self.port))
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
        except psycopg2.Error as ex:
            raise PostgresClientException from ex

    def run_queries(self, queries: Sequence[str]) -> list[Any]:
        """Run multiple queries and return results as a list."""
        results = []
        with self.connection.cursor() as cur:
            logger.info(f"Attempting to query data from database.")
            for query in queries:
                try:
                    cur.execute(query)
                except psycopg2.Error as ex:
                    raise PostgresClientException from ex

                if self.is_ddl_query(query):
                    self.connection.commit()

                result = cur.fetchall() if self.is_dql_query(query) else None
                results.append(result)
                self.connection.commit()
        logger.info(f"Successfully completed queues execution.")
        return results

    @staticmethod
    def is_ddl_query(query: str) -> bool:
        """Checks whether the query is a DDL query."""
        ddl_keywords = ["CREATE", "ALTER", "DROP", "TRUNCATE"]
        return next((True for keyword in ddl_keywords if keyword in query.upper()), False)

    @staticmethod
    def is_dql_query(query: str) -> bool:
        """Checks whether the query is a DQL query."""
        return query.upper().strip().startswith("SELECT")