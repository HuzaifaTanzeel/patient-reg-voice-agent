"""Read-only appointment and call lists used by the external dashboard."""

from tests.conftest import valid_patient_payload


async def test_lists_are_empty(client):
    appointments = await client.get("/appointments")
    calls = await client.get("/calls")
    assert appointments.status_code == 200
    assert calls.status_code == 200
    assert appointments.json() == {"data": [], "error": None}
    assert calls.json() == {"data": [], "error": None}


async def test_appointment_appears_after_booking(client):
    created = await client.post("/patients", json=valid_patient_payload())
    patient_id = created.json()["data"]["patient_id"]

    booked = await client.post(
        "/retell/tools/book_appointment",
        json={
            "call": {"call_id": "call_test_1"},
            "name": "book_appointment",
            "args": {
                "patient_id": patient_id,
                "slot_iso": "2026-09-28T14:00:00+00:00",
                "reason": "New patient visit",
            },
        },
    )
    assert booked.status_code == 200
    assert booked.json()["ok"] is True

    listed = await client.get("/appointments", params={"patient_id": patient_id})
    assert listed.status_code == 200
    rows = listed.json()["data"]
    assert len(rows) == 1
    assert rows[0]["patient_id"] == patient_id
    assert rows[0]["reason"] == "New patient visit"
    assert rows[0]["status"] == "scheduled"

    ended = await client.post(
        "/retell/webhook",
        json={
            "event": "call_analyzed",
            "call": {
                "call_id": "call_test_1",
                "from_number": "+14155550100",
                "to_number": "+14135554887",
                "disconnection_reason": "user_hangup",
                "transcript": "Agent: How can I help?",
                "call_analysis": {"call_summary": "Registered a new patient."},
            },
        },
    )
    assert ended.status_code == 200

    calls = await client.get("/calls")
    assert calls.status_code == 200
    row = calls.json()["data"][0]
    assert row["call_id"] == "call_test_1"
    assert row["summary"] == "Registered a new patient."
    assert row["transcript"] == "Agent: How can I help?"
