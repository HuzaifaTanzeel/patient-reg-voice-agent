"""Seed a couple of demo patients for local development / demos.

Idempotent: patients are matched by phone_number, so running it repeatedly will
not create duplicates. Run with:

    uv run python -m backend.scripts.seed
"""

import asyncio
from datetime import date

from backend.app.database import SessionLocal
from backend.app.models.patient import Sex
from backend.app.services import patients as patient_service

SEED_PATIENTS: list[dict] = [
    {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "date_of_birth": date(1990, 1, 15),
        "sex": Sex.FEMALE,
        "phone_number": "2025550143",
        "email": "ada@example.com",
        "address_line_1": "1 Main St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02101",
        "preferred_language": "English",
    },
    {
        "first_name": "Grace",
        "last_name": "Hopper",
        "date_of_birth": date(1985, 12, 9),
        "sex": Sex.FEMALE,
        "phone_number": "2025550188",
        "address_line_1": "47 Navy Yard",
        "city": "Arlington",
        "state": "VA",
        "zip_code": "22201",
        "insurance_provider": "Aetna",
        "insurance_member_id": "AET998877",
        "preferred_language": "English",
    },
]


async def main() -> None:
    created = 0
    async with SessionLocal() as session:
        for values in SEED_PATIENTS:
            existing = await patient_service.find_by_phone(
                session, values["phone_number"]
            )
            if existing is not None:
                print(
                    f"skip: {values['first_name']} {values['last_name']} "
                    f"({values['phone_number']}) already exists as {existing.patient_id}"
                )
                continue
            patient = await patient_service.create(session, values)
            created += 1
            print(
                f"created: {patient.first_name} {patient.last_name} -> "
                f"{patient.patient_id}"
            )
        await session.commit()
    print(f"done. created {created} patient(s).")


if __name__ == "__main__":
    asyncio.run(main())
