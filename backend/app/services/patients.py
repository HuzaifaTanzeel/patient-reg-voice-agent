"""Patient data-access layer.

Thin service functions shared by the REST routes, the Retell tool router, and the
dashboard so business logic lives in one place instead of being duplicated per
entrypoint. Functions operate on the ORM and return ORM instances (or ``None``);
HTTP concerns (status codes, envelopes) stay in the routers.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.patient import Patient


async def get_active(
    session: AsyncSession, patient_id: uuid.UUID
) -> Patient | None:
    """Return a non-deleted patient by id, or ``None`` if missing/soft-deleted."""
    patient = await session.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        return None
    return patient


async def find_by_phone(
    session: AsyncSession, phone_number: str
) -> Patient | None:
    """Return the most recent active patient with this phone number, if any.

    Used for duplicate detection when a returning caller is recognized.
    """
    stmt = (
        select(Patient)
        .where(Patient.deleted_at.is_(None))
        .where(Patient.phone_number == phone_number)
        .order_by(Patient.created_at.desc())
    )
    return (await session.scalars(stmt)).first()


async def list_patients(
    session: AsyncSession,
    *,
    last_name: str | None = None,
    date_of_birth: date | None = None,
    phone_number: str | None = None,
) -> list[Patient]:
    """List active patients, optionally filtered. Filters are already normalized."""
    stmt = select(Patient).where(Patient.deleted_at.is_(None))
    if last_name is not None and last_name.strip() != "":
        stmt = stmt.where(func.lower(Patient.last_name) == last_name.strip().lower())
    if date_of_birth is not None:
        stmt = stmt.where(Patient.date_of_birth == date_of_birth)
    if phone_number is not None and phone_number.strip() != "":
        stmt = stmt.where(Patient.phone_number == phone_number)
    stmt = stmt.order_by(Patient.created_at.desc())
    return list((await session.scalars(stmt)).all())


async def create(session: AsyncSession, values: dict) -> Patient:
    """Insert a new patient from a validated values dict and return it."""
    patient = Patient(**values)
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
    return patient


async def update(
    session: AsyncSession, patient: Patient, changes: dict
) -> Patient:
    """Apply partial changes to an existing patient and bump updated_at."""
    for field, value in changes.items():
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(patient)
    return patient


async def soft_delete(session: AsyncSession, patient: Patient) -> None:
    """Soft-delete a patient (set deleted_at); never hard-deletes."""
    now = datetime.now(timezone.utc)
    patient.deleted_at = now
    patient.updated_at = now
    await session.flush()
