"""Call record persistence (transcript / summary / dropped-call trace).

Rows are seeded when the agent invokes a tool (so we can link the call to the
patient it created or updated) and completed by the Retell webhook once the call
ends.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.call import Call


def _ms_to_dt(value: object) -> datetime | None:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    return None


async def link_patient(
    session: AsyncSession,
    call_id: str | None,
    *,
    patient_id: uuid.UUID | None = None,
    from_number: str | None = None,
    to_number: str | None = None,
) -> Call | None:
    """Create or update a call row, attaching patient / phone metadata."""
    if not call_id:
        return None
    call = await session.get(Call, call_id)
    if call is None:
        call = Call(call_id=call_id)
        session.add(call)
    if patient_id is not None:
        call.patient_id = patient_id
    if from_number:
        call.from_number = from_number
    if to_number:
        call.to_number = to_number
    call.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return call


async def record_webhook(session: AsyncSession, call_data: dict) -> Call | None:
    """Upsert a call row from a Retell webhook `call` object."""
    call_id = call_data.get("call_id")
    if not call_id:
        return None
    call = await session.get(Call, call_id)
    if call is None:
        call = Call(call_id=call_id)
        session.add(call)

    call.from_number = call_data.get("from_number") or call.from_number
    call.to_number = call_data.get("to_number") or call.to_number

    started = _ms_to_dt(call_data.get("start_timestamp"))
    ended = _ms_to_dt(call_data.get("end_timestamp"))
    if started is not None:
        call.started_at = started
    if ended is not None:
        call.ended_at = ended
    if call_data.get("start_timestamp") and call_data.get("end_timestamp"):
        call.duration_ms = int(
            call_data["end_timestamp"] - call_data["start_timestamp"]
        )

    call.disconnection_reason = (
        call_data.get("disconnection_reason") or call.disconnection_reason
    )
    call.transcript = call_data.get("transcript") or call.transcript

    analysis = call_data.get("call_analysis") or {}
    call.summary = analysis.get("call_summary") or call.summary

    call.raw = call_data
    call.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return call


async def list_calls(
    session: AsyncSession, patient_id: uuid.UUID | None = None
) -> list[Call]:
    from sqlalchemy import select

    stmt = select(Call).order_by(Call.created_at.desc())
    if patient_id is not None:
        stmt = stmt.where(Call.patient_id == patient_id)
    return list((await session.scalars(stmt)).all())


async def list_for_patient(
    session: AsyncSession, patient_id: uuid.UUID
) -> list[Call]:
    return await list_calls(session, patient_id)
