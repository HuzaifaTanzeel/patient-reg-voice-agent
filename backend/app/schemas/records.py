import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    scheduled_at: datetime
    reason: str | None
    status: str
    created_at: datetime


class CallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    call_id: str
    patient_id: uuid.UUID | None
    from_number: str | None
    to_number: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    disconnection_reason: str | None
    transcript: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime
