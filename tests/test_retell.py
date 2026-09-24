"""Retell integration tests: tool-call unwrapping, duplicate lookup, webhook."""

import json

from retell.lib.webhook_auth import symmetric

from tests.conftest import valid_patient_payload


def _tool_body(args: dict, call: dict | None = None) -> dict:
    return {"call": call or {"call_id": "call_abc"}, "name": "x", "args": args}


async def test_tool_create_unwraps_args(client):
    resp = await client.post(
        "/retell/tools/create_patient",
        json=_tool_body(
            valid_patient_payload(),
            call={"call_id": "call_1", "from_number": "+14155550100"},
        ),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["first_name"] == "Jane"
    assert "patient_id" in body


async def test_tool_create_invalid_returns_ok_false(client):
    resp = await client.post(
        "/retell/tools/create_patient",
        json=_tool_body(valid_patient_payload(phone_number="123")),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["errors"]


async def test_lookup_found_and_not_found(client):
    await client.post(
        "/retell/tools/create_patient",
        json=_tool_body(valid_patient_payload(phone_number="4155550100")),
    )

    found = await client.post(
        "/retell/tools/lookup_patient",
        json=_tool_body({"phone_number": "415-555-0100"}),
    )
    assert found.json()["found"] is True
    assert found.json()["first_name"] == "Jane"

    missing = await client.post(
        "/retell/tools/lookup_patient",
        json=_tool_body({"phone_number": "9999999999"}),
    )
    assert missing.json()["found"] is False


async def test_lookup_uses_caller_id_when_no_arg(client):
    await client.post(
        "/retell/tools/create_patient",
        json=_tool_body(valid_patient_payload(phone_number="2025550143")),
    )
    resp = await client.post(
        "/retell/tools/lookup_patient",
        json=_tool_body({}, call={"from_number": "+1 (202) 555-0143"}),
    )
    assert resp.json()["found"] is True


async def test_appointment_slots_and_booking(client):
    created = await client.post(
        "/retell/tools/create_patient", json=_tool_body(valid_patient_payload())
    )
    patient_id = created.json()["patient_id"]

    slots = await client.post("/retell/tools/get_available_slots", json=_tool_body({}))
    slot_list = slots.json()["slots"]
    assert len(slot_list) == 3
    assert "iso" in slot_list[0] and "label" in slot_list[0]

    booked = await client.post(
        "/retell/tools/book_appointment",
        json=_tool_body(
            {
                "patient_id": patient_id,
                "slot_iso": slot_list[0]["iso"],
                "reason": "New patient visit",
            }
        ),
    )
    assert booked.json()["ok"] is True
    assert "when" in booked.json()


async def test_update_via_tool(client):
    created = await client.post(
        "/retell/tools/create_patient", json=_tool_body(valid_patient_payload())
    )
    patient_id = created.json()["patient_id"]

    updated = await client.post(
        "/retell/tools/update_patient",
        json=_tool_body({"patient_id": patient_id, "city": "Berkeley"}),
    )
    assert updated.json()["ok"] is True

    check = await client.get(f"/patients/{patient_id}")
    assert check.json()["data"]["city"] == "Berkeley"


async def test_webhook_stores_transcript(client):
    created = await client.post(
        "/retell/tools/create_patient",
        json=_tool_body(
            valid_patient_payload(), call={"call_id": "call_wh", "from_number": "+1"}
        ),
    )
    patient_id = created.json()["patient_id"]

    event = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_wh",
            "transcript": "Agent: Hi\nUser: Register me",
            "disconnection_reason": "user_hangup",
            "start_timestamp": 1790000000000,
            "end_timestamp": 1790000060000,
            "call_analysis": {"call_summary": "Registered a new patient."},
        },
    }
    resp = await client.post("/retell/webhook", json=event)
    assert resp.status_code == 200

    detail = await client.get(f"/dashboard/patients/{patient_id}")
    assert "Registered a new patient." in detail.text
    assert "Register me" in detail.text


async def test_webhook_rejects_bad_signature(client, monkeypatch):
    from backend.app.routes import retell as retell_route

    monkeypatch.setattr(retell_route.settings, "verify_retell_signature", True)
    monkeypatch.setattr(retell_route.settings, "retell_api_key", "secret-key")

    payload = {"event": "call_ended", "call": {"call_id": "call_sig"}}
    raw = json.dumps(payload)

    bad = await client.post(
        "/retell/webhook",
        content=raw,
        headers={"x-retell-signature": "deadbeef", "content-type": "application/json"},
    )
    assert bad.status_code == 401

    good_sig = symmetric["sign"](raw, "secret-key")
    good = await client.post(
        "/retell/webhook",
        content=raw,
        headers={
            "x-retell-signature": good_sig,
            "content-type": "application/json",
        },
    )
    assert good.status_code == 200
