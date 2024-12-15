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

from fastapi import APIRouter, HTTPException

from timer_queue.client import RabbitMQClient
from webserver.database.engine import SessionDep
from webserver.models.timers import (
    Timers,
    TimerCreateIn,
    TimerCreateOut,
    TimerGetOut,
)

RABBIT_MQ_HOST = os.environ.get("RABBIT_MQ_HOST", "0.0.0.0")
RABBIT_MQ_PORT = int(os.environ.get("RABBIT_MQ_PORT", "5672"))
RABBIT_MQ_INCOMING = os.environ.get("RABBIT_MQ_INCOMING", "unknown_incoming")


router = APIRouter(prefix="/timer", tags=["timer"])


@router.post("/", response_model=TimerCreateOut)
def create_timer(timer: TimerCreateIn) -> TimerCreateOut:
    """
    Create a new timer.

    Returns:
        Health: A dictionary containing the status of the application.
    """
    timer_db = Timers(**timer.model_dump())

    client = RabbitMQClient(host=RABBIT_MQ_HOST, port=RABBIT_MQ_PORT)
    client.push_message(queue_name=RABBIT_MQ_INCOMING, message=timer_db.dumps())

    return TimerCreateOut(id=timer_db.id)


@router.get("/{id}", response_model=TimerGetOut)
def get_timer(id: str, session: SessionDep) -> TimerGetOut:
    if timer := session.get(Timers, id):
        return TimerGetOut(id=timer.id, time_left=timer.time_left)
    raise HTTPException(status_code=404, detail="Timer not found")
