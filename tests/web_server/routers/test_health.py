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

from fastapi.testclient import TestClient

from webserver.main import app


class TestHealthEndpoints:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    @mock.patch("fastapi.testclient.TestClient.get")
    def test_health_404(self, mock_get: mock.MagicMock) -> None:
        mock_get.return_value.status_code = 404

        response = self.client.get("/health")
        assert response.status_code == 404

    @mock.patch("fastapi.testclient.TestClient.get")
    def test_health_not_ok(self, mock_get: mock.MagicMock) -> None:
        mock_json = {"status": "Test error message"}
        mock_get.return_value = mock.MagicMock(status_code=200, json=mock.MagicMock(return_value=mock_json))
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == mock_json
