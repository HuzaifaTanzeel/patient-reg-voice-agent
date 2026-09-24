"""Retell integration endpoints.

Two kinds of inbound requests from Retell:

1. Custom function (tool) calls -> POST /retell/tools/{name}. Retell sends
   ``{"call": {...}, "name": "...", "args": {...}}`` (function config uses
   ``args_at_root: false``). We validate ``args`` with the same Pydantic schemas
   the REST API uses, run the shared service layer, and return small,
   speech-friendly JSON the agent can relay.
2. Webhook events -> POST /retell/webhook (call_started / call_ended /
   call_analyzed), signed with ``x-retell-signature``. Used to persist the
   transcript, summary, and disconnection reason (also the dropped-call trace).
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_session
from backend.app.schemas.patient import PatientCreate, PatientUpdate
from backend.app.services import appointments as appt_service
from backend.app.services import calls as calls_service
from backend.app.services import patients as patient_service
from backend.app.validation import normalize_us_phone

router = APIRouter(prefix="/retell", tags=["retell"])
logger = logging.getLogger("patient_reg.retell")


def _format_errors(exc: ValidationError) -> list[str]:
    messages = []
    for err in exc.errors():
        field = ".".join(str(part) for part in err.get("loc", ())) or "field"
        messages.append(f"{field}: {err.get('msg')}")
    return messages


async def _tool_body(request: Request) -> tuple[dict, dict]:
    """Return (args, call) from a Retell tool-call request body."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - malformed JSON from an unexpected caller
        return {}, {}
    if not isinstance(body, dict):
        return {}, {}
    args = body.get("args") if isinstance(body.get("args"), dict) else {}
    call = body.get("call") if isinstance(body.get("call"), dict) else {}
    return args, call


# --------------------------------------------------------------------------- #
# Tool calls
# --------------------------------------------------------------------------- #
@router.post("/tools/create_patient")
async def tool_create_patient(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    args, call = await _tool_body(request)
    try:
        payload = PatientCreate.model_validate(args)
    except ValidationError as exc:
        return {
            "ok": False,
            "message": "Some of the details weren't valid. Please re-check them.",
            "errors": _format_errors(exc),
        }
    patient = await patient_service.create(session, payload.model_dump())
    await calls_service.link_patient(
        session,
        call.get("call_id"),
        patient_id=patient.patient_id,
        from_number=call.get("from_number"),
        to_number=call.get("to_number"),
    )
    logger.info(
        "retell.tool create_patient call_id=%s patient_id=%s payload=%s",
        call.get("call_id"),
        patient.patient_id,
        json.dumps(payload.model_dump(mode="json"), default=str),
    )
    return {
        "ok": True,
        "patient_id": str(patient.patient_id),
        "first_name": patient.first_name,
        "message": f"Registered {patient.first_name} successfully.",
    }


@router.post("/tools/lookup_patient")
async def tool_lookup_patient(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    args, call = await _tool_body(request)
    raw_phone = args.get("phone_number") or call.get("from_number")
    if not raw_phone:
        return {"found": False, "message": "No phone number was provided."}
    try:
        phone = normalize_us_phone(str(raw_phone))
    except ValueError:
        return {"found": False, "message": "That phone number wasn't valid."}
    patient = await patient_service.find_by_phone(session, phone)
    if patient is None:
        return {"found": False}
    return {
        "found": True,
        "patient_id": str(patient.patient_id),
        "first_name": patient.first_name,
        "last_name": patient.last_name,
    }


@router.post("/tools/update_patient")
async def tool_update_patient(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    args, call = await _tool_body(request)
    patient_id = args.pop("patient_id", None)
    if not patient_id:
        return {"ok": False, "message": "No patient id was provided to update."}
    try:
        parsed_id = uuid.UUID(str(patient_id))
    except ValueError:
        return {"ok": False, "message": "That patient id wasn't valid."}
    try:
        payload = PatientUpdate.model_validate(args)
    except ValidationError as exc:
        return {
            "ok": False,
            "message": "Some of the updated details weren't valid.",
            "errors": _format_errors(exc),
        }
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"ok": False, "message": "There was nothing to update."}
    patient = await patient_service.get_active(session, parsed_id)
    if patient is None:
        return {"ok": False, "message": "We couldn't find that patient record."}
    patient = await patient_service.update(session, patient, changes)
    await calls_service.link_patient(
        session, call.get("call_id"), patient_id=patient.patient_id
    )
    logger.info(
        "retell.tool update_patient call_id=%s patient_id=%s fields=%s",
        call.get("call_id"),
        patient.patient_id,
        list(changes.keys()),
    )
    return {
        "ok": True,
        "patient_id": str(patient.patient_id),
        "first_name": patient.first_name,
        "message": f"Updated {patient.first_name}'s information.",
    }


@router.post("/tools/get_available_slots")
async def tool_get_available_slots(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    await _tool_body(request)
    slots = await appt_service.available_slots(session, count=3)
    return {
        "slots": [
            {"iso": slot.isoformat(), "label": appt_service.slot_label(slot)}
            for slot in slots
        ]
    }


@router.post("/tools/book_appointment")
async def tool_book_appointment(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    args, call = await _tool_body(request)
    patient_id = args.get("patient_id")
    slot_iso = args.get("slot_iso") or args.get("iso") or args.get("slot")
    reason = args.get("reason")
    if not patient_id or not slot_iso:
        return {"ok": False, "message": "A patient and a time slot are required."}
    try:
        parsed_id = uuid.UUID(str(patient_id))
    except ValueError:
        return {"ok": False, "message": "That patient id wasn't valid."}
    try:
        scheduled_at = datetime.fromisoformat(str(slot_iso))
    except ValueError:
        return {"ok": False, "message": "That appointment time wasn't valid."}
    patient = await patient_service.get_active(session, parsed_id)
    if patient is None:
        return {"ok": False, "message": "We couldn't find that patient record."}
    appointment = await appt_service.book(
        session, parsed_id, scheduled_at, reason=reason
    )
    label = appt_service.slot_label(scheduled_at)
    logger.info(
        "retell.tool book_appointment call_id=%s patient_id=%s at=%s",
        call.get("call_id"),
        parsed_id,
        scheduled_at.isoformat(),
    )
    return {
        "ok": True,
        "appointment_id": str(appointment.appointment_id),
        "when": label,
        "message": f"Booked an appointment for {label}.",
    }


# --------------------------------------------------------------------------- #
# Webhook
# --------------------------------------------------------------------------- #
def _verify_signature(body: bytes, signature: str | None) -> bool:
    if not settings.verify_retell_signature:
        return True
    if not settings.retell_api_key or not signature:
        return False
    expected = hmac.new(
        settings.retell_api_key.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def retell_webhook(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    raw = await request.body()
    signature = request.headers.get("x-retell-signature")
    if not _verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="Invalid Retell signature")
    try:
        body = json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event = body.get("event")
    call_data = body.get("call") if isinstance(body.get("call"), dict) else {}

    if event in ("call_ended", "call_analyzed"):
        call = await calls_service.record_webhook(session, call_data)
        logger.info(
            "retell.webhook event=%s call_id=%s disconnection=%s summary=%s",
            event,
            call_data.get("call_id"),
            call_data.get("disconnection_reason"),
            (call.summary[:120] if call and call.summary else None),
        )
    elif event == "call_started":
        await calls_service.link_patient(
            session,
            call_data.get("call_id"),
            from_number=call_data.get("from_number"),
            to_number=call_data.get("to_number"),
        )
        logger.info(
            "retell.webhook event=call_started call_id=%s",
            call_data.get("call_id"),
        )

    return {"ok": True}
