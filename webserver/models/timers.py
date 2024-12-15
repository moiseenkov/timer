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
import uuid
from datetime import datetime, timedelta
from typing import Any

import pydantic
import sqlmodel

from webserver.utils.timer import utc_now


class Timers(sqlmodel.SQLModel, table=True):
    """
    Main database model represents a delayed call for the URL.
    """
    id: uuid.UUID = sqlmodel.Field(default_factory=uuid.uuid4, primary_key=True, description="The UUID of the timer", include=True)
    hours: int = sqlmodel.Field(ge=0, description="The number of hours the timer will run")
    minutes: int = sqlmodel.Field(ge=0, description="The number of minutes the timer will run")
    seconds: int = sqlmodel.Field(ge=0, description="The number of seconds the timer will run")
    url: str = sqlmodel.Field(description="The URL of the timer")
    created_at: datetime = sqlmodel.Field(default_factory=utc_now, description="The date and time the timer was created")

    @property
    def fire_at(self) -> datetime:
        """Retrieves date and time the timer should be fired."""
        return self.created_at + timedelta(hours=self.hours, minutes=self.minutes, seconds=self.seconds)

    @property
    def time_left(self) -> int:
        """Retrieves the amount of seconds the timer should run. If it expired, then returns 0"""
        now = utc_now()
        if self.fire_at > now:
            return (self.fire_at - now).seconds
        return 0

    def dumps(self, *args, **kwargs) -> dict[str, Any]:
        """Retrieves fully serializable JSON object for the model instance."""
        data = self.model_dump(*args, **kwargs)
        data["id"] = str(data["id"])
        data["created_at"] = str(data["created_at"])
        data["fire_at"] = str(self.fire_at)
        return data


class TimerCreateIn(pydantic.BaseModel):
    """Timer input model represents a delayed call for the URL."""
    hours: int = pydantic.Field(ge=0, description="The number of hours the timer will run")
    minutes: int = pydantic.Field(ge=0, description="The number of minutes the timer will run")
    seconds: int = pydantic.Field(ge=0, description="The number of seconds the timer will run")
    url: str = pydantic.Field(description="The URL of the timer")


class TimerCreateOut(pydantic.BaseModel):
    """Timer output model for create requests represents a delayed call for the URL."""
    id: uuid.UUID = pydantic.Field(description="The UUID of the timer")


class TimerGetOut(pydantic.BaseModel):
    """Timer output model for get requests represents a delayed call for the URL."""
    id: uuid.UUID = pydantic.Field(description="The UUID of the timer")
    time_left: int = pydantic.Field(description="The time left in seconds")
