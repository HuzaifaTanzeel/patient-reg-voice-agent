"""Read-only JSON for the external dashboard (patients stay on /patients)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.envelopes import Envelope
from backend.app.schemas.records import AppointmentResponse, CallResponse
from backend.app.services import appointments as appt_service
from backend.app.services import calls as calls_service

router = APIRouter(tags=["records"])


@router.get("/appointments", response_model=Envelope[list[AppointmentResponse]])
async def list_appointments(
    patient_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Envelope[list[AppointmentResponse]]:
    rows = await appt_service.list_appointments(session, patient_id)
    return Envelope(data=[AppointmentResponse.model_validate(row) for row in rows])


@router.get("/calls", response_model=Envelope[list[CallResponse]])
async def list_calls(
    patient_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Envelope[list[CallResponse]]:
    rows = await calls_service.list_calls(session, patient_id)
    return Envelope(data=[CallResponse.model_validate(row) for row in rows])
