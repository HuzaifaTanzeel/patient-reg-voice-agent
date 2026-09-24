"""Server-rendered dashboard for viewing registered patients.

Same-origin Jinja2 pages (no build step, no separate deploy). Read-only: a quick
way for a reviewer to see patients, their appointments, and linked call
transcripts/summaries straight from the database.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.services import appointments as appt_service
from backend.app.services import calls as calls_service
from backend.app.services import patients as patient_service
from backend.app.services.appointments import slot_label
from backend.app.validation import normalize_us_phone

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["slot_label"] = slot_label

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    last_name: str | None = Query(default=None),
    phone_number: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    phone_filter: str | None = None
    if phone_number and phone_number.strip():
        try:
            phone_filter = normalize_us_phone(phone_number)
        except ValueError:
            # Invalid input -> guaranteed no match rather than a 422 in the UI.
            phone_filter = "__no_match__"

    patients = await patient_service.list_patients(
        session,
        last_name=last_name,
        phone_number=phone_filter,
    )
    return templates.TemplateResponse(
        request,
        "patients.html",
        {
            "patients": patients,
            "last_name": last_name or "",
            "phone_number": phone_number or "",
            "count": len(patients),
        },
    )


@router.get("/dashboard/patients/{patient_id}", response_class=HTMLResponse)
async def dashboard_detail(
    patient_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    patient = await patient_service.get_active(session, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    appointments = await appt_service.list_for_patient(session, patient_id)
    calls = await calls_service.list_for_patient(session, patient_id)
    return templates.TemplateResponse(
        request,
        "patient_detail.html",
        {
            "patient": patient,
            "appointments": appointments,
            "calls": calls,
        },
    )
