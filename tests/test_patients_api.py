"""REST API tests: CRUD, envelope shape, validation, soft delete, filters."""

from tests.conftest import valid_patient_payload


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_and_get_patient(client):
    resp = await client.post("/patients", json=valid_patient_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["first_name"] == "Jane"
    assert data["phone_number"] == "4155550100"
    assert data["preferred_language"] == "English"
    patient_id = data["patient_id"]

    got = await client.get(f"/patients/{patient_id}")
    assert got.status_code == 200
    assert got.json()["data"]["patient_id"] == patient_id


async def test_phone_is_normalized_on_create(client):
    resp = await client.post(
        "/patients", json=valid_patient_payload(phone_number="(415) 555-0177")
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["phone_number"] == "4155550177"


async def test_future_dob_rejected(client):
    resp = await client.post(
        "/patients", json=valid_patient_payload(date_of_birth="2999-01-01")
    )
    assert resp.status_code == 422


async def test_short_phone_rejected(client):
    resp = await client.post(
        "/patients", json=valid_patient_payload(phone_number="123")
    )
    assert resp.status_code == 422


async def test_bad_state_rejected(client):
    resp = await client.post(
        "/patients", json=valid_patient_payload(state="ZZ")
    )
    assert resp.status_code == 422


async def test_unknown_field_rejected(client):
    resp = await client.post(
        "/patients", json=valid_patient_payload(nickname="Janey")
    )
    assert resp.status_code == 422


async def test_get_missing_patient_404(client):
    resp = await client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_list_filters(client):
    await client.post(
        "/patients",
        json=valid_patient_payload(last_name="Smith", phone_number="2025550111"),
    )
    await client.post(
        "/patients",
        json=valid_patient_payload(last_name="Jones", phone_number="2025550222"),
    )

    by_name = await client.get("/patients", params={"last_name": "smith"})
    assert by_name.status_code == 200
    rows = by_name.json()["data"]
    assert len(rows) == 1 and rows[0]["last_name"] == "Smith"

    by_phone = await client.get("/patients", params={"phone_number": "202-555-0222"})
    assert len(by_phone.json()["data"]) == 1
    assert by_phone.json()["data"][0]["last_name"] == "Jones"


async def test_soft_delete_hides_but_keeps(client):
    created = await client.post("/patients", json=valid_patient_payload())
    patient_id = created.json()["data"]["patient_id"]

    deleted = await client.delete(f"/patients/{patient_id}")
    assert deleted.status_code == 200

    assert (await client.get(f"/patients/{patient_id}")).status_code == 404
    listed = await client.get("/patients")
    assert all(p["patient_id"] != patient_id for p in listed.json()["data"])


async def test_update_partial(client):
    created = await client.post("/patients", json=valid_patient_payload())
    patient_id = created.json()["data"]["patient_id"]

    updated = await client.put(
        f"/patients/{patient_id}", json={"city": "Oakland", "state": "CA"}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["city"] == "Oakland"


async def test_update_empty_body_400(client):
    created = await client.post("/patients", json=valid_patient_payload())
    patient_id = created.json()["data"]["patient_id"]

    resp = await client.put(f"/patients/{patient_id}", json={})
    assert resp.status_code == 400
