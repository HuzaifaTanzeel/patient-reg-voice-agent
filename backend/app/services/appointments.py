"""Appointment scheduling with mock availability.

Slots are generated deterministically (next weekdays at fixed clinic hours) rather
than stored in a calendar system - enough to demo the "offer a first appointment"
flow without a real scheduling backend.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.appointment import Appointment

# Clinic offers these hours (UTC for simplicity in this demo).
SLOT_HOURS = (9, 11, 14, 16)


def _candidate_slots(count: int) -> list[datetime]:
    """Return the next `count` weekday slots starting tomorrow."""
    slots: list[datetime] = []
    day = datetime.now(timezone.utc).date() + timedelta(days=1)
    while len(slots) < count:
        if day.weekday() < 5:  # Monday-Friday only
            for hour in SLOT_HOURS:
                slots.append(
                    datetime(day.year, day.month, day.day, hour, 0, tzinfo=timezone.utc)
                )
                if len(slots) >= count:
                    break
        day += timedelta(days=1)
    return slots


def slot_label(slot: datetime) -> str:
    """Human/voice-friendly label, e.g. 'Monday, Sep 28 at 9:00 AM'.

    Built manually to stay portable (``%-I`` is not supported on Windows).
    """
    hour12 = slot.hour % 12 or 12
    meridiem = "AM" if slot.hour < 12 else "PM"
    return f"{slot.strftime('%A, %b %d')} at {hour12}:{slot.minute:02d} {meridiem}"


async def available_slots(
    session: AsyncSession, *, count: int = 3
) -> list[datetime]:
    """Return up to `count` upcoming slots not already booked."""
    candidates = _candidate_slots(count * 3)
    booked = set(
        (
            await session.scalars(
                select(Appointment.scheduled_at).where(
                    Appointment.status == "scheduled"
                )
            )
        ).all()
    )
    free = [slot for slot in candidates if slot not in booked]
    return free[:count]


async def book(
    session: AsyncSession,
    patient_id: uuid.UUID,
    scheduled_at: datetime,
    reason: str | None = None,
) -> Appointment:
    appointment = Appointment(
        patient_id=patient_id, scheduled_at=scheduled_at, reason=reason
    )
    session.add(appointment)
    await session.flush()
    await session.refresh(appointment)
    return appointment


async def list_appointments(
    session: AsyncSession, patient_id: uuid.UUID | None = None
) -> list[Appointment]:
    stmt = select(Appointment).order_by(Appointment.scheduled_at.desc())
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    return list((await session.scalars(stmt)).all())


async def list_for_patient(
    session: AsyncSession, patient_id: uuid.UUID
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.scheduled_at)
    )
    return list((await session.scalars(stmt)).all())
