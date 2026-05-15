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


@app.post("/v1/requests", status_code=201)
async def register_request(body: NotificationRequest) -> dict:
    record = RequestRecord(
        id=str(uuid.uuid4()),
        to=body.to,
        message=body.message,
        type=body.type,
        status=NotificationStatus.queued,
    )
    async with _store_lock:
        _store[record.id] = record
    return {"id": record.id}


@app.get("/v1/requests/{request_id}")
async def get_request_status(request_id: str) -> dict:
    async with _store_lock:
        record = _store.get(request_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Request not found")
    return {"id": record.id, "status": record.status}
