"""Pytest fixtures: a real Postgres test database and an ASGI httpx client.

Uses a separate database (default: patient_reg_test on the local Postgres) so it
never touches dev/prod data. Tables are created from the SQLAlchemy models (which
carry the same constraints as the Alembic migration), and every test starts from a
truncated, empty schema.

Override the target with the TEST_DATABASE_URL env var.
"""

import asyncio
import os

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("VERIFY_RETELL_SIGNATURE", "false")

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/patient_reg_test",
)


def _db_name() -> str:
    return TEST_DATABASE_URL.rsplit("/", 1)[1]


def _admin_dsn() -> str:
    base = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    return base.replace("postgresql+asyncpg://", "postgresql://")


async def _ensure_database_and_tables() -> None:
    from backend.app.database import Base
    import backend.app.models  # noqa: F401  (register all mappers)

    conn = await asyncpg.connect(_admin_dsn())
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _db_name()
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_db_name()}"')
    finally:
        await conn.close()

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    asyncio.run(_ensure_database_and_tables())
    yield


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    from backend.app.database import get_session
    from backend.app.main import app

    engine = create_async_engine(TEST_DATABASE_URL)
    test_sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE calls, appointments, patients RESTART IDENTITY CASCADE")
        )

    async def _get_test_session():
        async with test_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _get_test_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()
    await engine.dispose()


def valid_patient_payload(**overrides) -> dict:
    payload = {
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "1990-05-20",
        "sex": "Female",
        "phone_number": "4155550100",
        "address_line_1": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94105",
    }
    payload.update(overrides)
    return payload
