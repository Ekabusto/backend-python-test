import asyncio
import uuid
from enum import Enum
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Notification Service (Technical Test)")


class NotificationStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    sent = "sent"
    failed = "failed"


class NotificationRequest(BaseModel):
    to: str
    message: str
    type: Literal["email", "sms", "push"]


class RequestRecord(BaseModel):
    id: str
    to: str
    message: str
    type: str
    status: NotificationStatus


_store: dict[str, RequestRecord] = {}
_store_lock = asyncio.Lock()
