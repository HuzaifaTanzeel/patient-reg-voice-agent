import json
import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.envelopes import Envelope
from backend.app.models.patient import Patient
from backend.app.schemas.patient import (
    DeleteResult,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from backend.app.services import patients as patient_service
from backend.app.validation import normalize_us_phone, parse_date_of_birth

router = APIRouter(prefix="/patients", tags=["patients"])
logger = logging.getLogger("patient_reg.patients")


def _log_payload(action: str, payload: dict) -> None:
    logger.info("%s final_payload=%s", action, json.dumps(payload, default=str))


async def _require_active_patient(
    session: AsyncSession, patient_id: uuid.UUID
) -> Patient:
    patient = await patient_service.get_active(session, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _parse_dob_filter(value: str) -> date:
    try:
        return parse_date_of_birth(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"date_of_birth {exc}") from exc


def _parse_phone_filter(value: str) -> str:
    try:
        return normalize_us_phone(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"phone_number {exc}") from exc


@router.get("", response_model=Envelope[list[PatientResponse]])
async def list_patients(
    last_name: str | None = Query(default=None),
    date_of_birth: str | None = Query(default=None),
    phone_number: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Envelope[list[PatientResponse]]:
    dob_filter = (
        _parse_dob_filter(date_of_birth)
        if date_of_birth is not None and date_of_birth.strip() != ""
        else None
    )
    phone_filter = (
        _parse_phone_filter(phone_number)
        if phone_number is not None and phone_number.strip() != ""
        else None
    )
    rows = await patient_service.list_patients(
        session,
        last_name=last_name,
        date_of_birth=dob_filter,
        phone_number=phone_filter,
    )
    return Envelope(data=[PatientResponse.model_validate(row) for row in rows])


@router.get("/{patient_id}", response_model=Envelope[PatientResponse])
async def get_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Envelope[PatientResponse]:
    patient = await _require_active_patient(session, patient_id)
    return Envelope(data=PatientResponse.model_validate(patient))


@router.post("", response_model=Envelope[PatientResponse], status_code=201)
async def create_patient(
    payload: PatientCreate,
    session: AsyncSession = Depends(get_session),
) -> Envelope[PatientResponse]:
    patient = await patient_service.create(session, payload.model_dump())
    body = PatientResponse.model_validate(patient)
    _log_payload("patient.create", body.model_dump(mode="json"))
    return Envelope(data=body)


@router.put("/{patient_id}", response_model=Envelope[PatientResponse])
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    session: AsyncSession = Depends(get_session),
) -> Envelope[PatientResponse]:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    patient = await _require_active_patient(session, patient_id)
    patient = await patient_service.update(session, patient, changes)
    body = PatientResponse.model_validate(patient)
    _log_payload("patient.update", body.model_dump(mode="json"))
    return Envelope(data=body)


@router.delete("/{patient_id}", response_model=Envelope[DeleteResult])
async def delete_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Envelope[DeleteResult]:
    patient = await _require_active_patient(session, patient_id)
    await patient_service.soft_delete(session, patient)
    return Envelope(data=DeleteResult(message="Patient deleted"))
