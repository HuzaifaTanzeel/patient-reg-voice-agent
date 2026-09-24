import json
import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
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
from backend.app.validation import normalize_us_phone, parse_date_of_birth

router = APIRouter(prefix="/patients", tags=["patients"])
logger = logging.getLogger("patient_reg.patients")


def _log_payload(action: str, payload: dict) -> None:
    logger.info("%s final_payload=%s", action, json.dumps(payload, default=str))


async def _get_active_patient(session: AsyncSession, patient_id: uuid.UUID) -> Patient:
    patient = await session.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
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
    stmt = select(Patient).where(Patient.deleted_at.is_(None))
    if last_name is not None and last_name.strip() != "":
        stmt = stmt.where(func.lower(Patient.last_name) == last_name.strip().lower())
    if date_of_birth is not None and date_of_birth.strip() != "":
        stmt = stmt.where(Patient.date_of_birth == _parse_dob_filter(date_of_birth))
    if phone_number is not None and phone_number.strip() != "":
        stmt = stmt.where(Patient.phone_number == _parse_phone_filter(phone_number))
    stmt = stmt.order_by(Patient.created_at.desc())
    rows = (await session.scalars(stmt)).all()
    return Envelope(data=[PatientResponse.model_validate(row) for row in rows])


@router.get("/{patient_id}", response_model=Envelope[PatientResponse])
async def get_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Envelope[PatientResponse]:
    patient = await _get_active_patient(session, patient_id)
    return Envelope(data=PatientResponse.model_validate(patient))


@router.post("", response_model=Envelope[PatientResponse], status_code=201)
async def create_patient(
    payload: PatientCreate,
    session: AsyncSession = Depends(get_session),
) -> Envelope[PatientResponse]:
    patient = Patient(**payload.model_dump())
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
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
    patient = await _get_active_patient(session, patient_id)
    for field, value in changes.items():
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(patient)
    body = PatientResponse.model_validate(patient)
    _log_payload("patient.update", body.model_dump(mode="json"))
    return Envelope(data=body)


@router.delete("/{patient_id}", response_model=Envelope[DeleteResult])
async def delete_patient(
    patient_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Envelope[DeleteResult]:
    patient = await _get_active_patient(session, patient_id)
    patient.deleted_at = datetime.now(timezone.utc)
    patient.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return Envelope(data=DeleteResult(message="Patient deleted"))
