import asyncio
import uuid
from enum import Enum
from typing import Literal

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from provider_client import ProviderError, send_notification

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


# Guardo todo en memoria por ahora, si esto escalara habría que meter una BD (logico)
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


async def _process_notification(request_id: str) -> None:
    # Primero marco como processing para que el cliente sepa que ya está en marcha
    async with _store_lock:
        record = _store.get(request_id)
        if record is None:
            return
        _store[request_id] = record.model_copy(update={"status": NotificationStatus.processing})

    try:
        await send_notification(record.to, record.message, record.type)
        new_status = NotificationStatus.sent
    except ProviderError:
        # Si falla después de todos los reintentos no queda otra que marcarlo como failed
        new_status = NotificationStatus.failed

    async with _store_lock:
        record = _store.get(request_id)
        if record:
            _store[request_id] = record.model_copy(update={"status": new_status})


@app.post("/v1/requests/{request_id}/process", status_code=202)
async def process_request(request_id: str, background_tasks: BackgroundTasks) -> dict:
    async with _store_lock:
        record = _store.get(request_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Request not found")

    # Lanzo el envío en background para no bloquear la respuesta al cliente
    background_tasks.add_task(_process_notification, request_id)
    return {"id": request_id, "status": "processing"}
