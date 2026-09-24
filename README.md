# Patient Registration Voice Agent

A phone intake agent that registers patients into Postgres. Retell handles the call (speech-to-text, the conversation model, and text-to-speech). This FastAPI service owns the data: patient records, mock appointments, and call transcripts.

**Call the agent:** +1 (413) 848-7102

**API:** https://api-production-57f92.up.railway.app

**Dashboard:** [https://api-production-57f92.up.railway.app/dashboard](https://gravity-vision-spark.lovable.app/)

## Architecture

```
Caller --> Retell (STT / LLM / TTS)
             |  POST /retell/tools/*          custom tools (args wrapped with call id)
             |  POST /retell/webhook          call_started / call_ended / call_analyzed
             v
        FastAPI
             |  /patients          REST CRUD (same service layer)
             |  /dashboard         Jinja2, same origin
             v
        Postgres (patients, appointments, calls)
```

Telephony stays in Retell. The API never sees audio. Tools post to `/retell/tools/*` with `args_at_root: false`, so every call carries `call.call_id` and can be linked to the patient it created or updated. The webhook later attaches the transcript and summary.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Voice | Retell AI | Phone number, STT/TTS, and tool calling without running a media server |
| API | FastAPI + Pydantic | Validation and status codes come from the schemas |
| DB | PostgreSQL | Relational patient data; Docker locally, Railway in production |
| UI | Jinja2 | Same process as the API, no frontend build |
| Host | Railway | Public HTTPS so Retell can reach the tools and webhook |

## API

All JSON responses use `{ "data": ..., "error": ... }`.

| Method | Path | Notes |
|---|---|---|
| POST | `/patients` | 201. Validates DOB (past), 10-digit US phone, 2-letter state, ZIP |
| GET | `/patients/{id}` | 404 if missing or soft-deleted |
| GET | `/patients` | Optional `last_name`, `date_of_birth`, `phone_number` |
| PUT | `/patients/{id}` | Partial update. Empty body is 400 |
| DELETE | `/patients/{id}` | Soft delete (`deleted_at`) |
| GET | `/health` | Liveness |
| GET | `/dashboard` | Patient list, filter by last name or phone |
| GET | `/dashboard/patients/{id}` | Record, appointments, transcripts |

Retell tools (speech-friendly JSON, not the REST envelope): `POST /retell/tools/create_patient`, `lookup_patient`, `update_patient`, `get_available_slots`, `book_appointment`. `POST /retell/webhook` verifies `x-retell-signature`.

## Local setup

Requires Docker, Python 3.11+, and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d
cp .env.example .env
uv sync --all-groups
uv run alembic upgrade head
uv run python -m backend.scripts.seed
uv run uvicorn backend.app.main:app --reload
```

Seed is idempotent by phone number and inserts two demo patients (Ada Lovelace, Grace Hopper).

```bash
uv run pytest
```

Tests use a separate database, `patient_reg_test`, on the same local Postgres. Override with `TEST_DATABASE_URL`.

### Environment

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async Postgres URL (`postgresql+asyncpg://...`) |
| `RETELL_API_KEY` | Verifies webhook signatures. Also used by scripts that call the Retell API |
| `VERIFY_RETELL_SIGNATURE` | `true` in production. Set `false` only for unsigned local calls |

## Retell agent

Agent `agent_cef430473eb97beb8523e434bf`, LLM `llm_399dc8cd548f15a8b34abb506a32`, voice `11labs-Brian`. Prompt, begin message, and tool definitions live in [`retell/`](retell/).

The prompt batches questions, confirms once before saving, looks up the phone number for returning callers, offers a first appointment after a successful save, and switches to Spanish when the caller does.

## Edge cases

- **Invalid DOB, phone, state, or ZIP.** The API returns 422. On a tool call the agent gets `ok: false` and re-asks only that field.
- **Dropped call.** `call_ended` / `call_analyzed` still upsert a `calls` row (transcript, summary, `disconnection_reason`), even when no patient was saved.
- **Database write failure.** The tool returns a failure payload. The agent tells the caller someone will follow up and ends the call. It does not pretend the save worked.
- **Start over.** The prompt discards the affected details and continues, keeping anything the caller did not scrap.

## Known limitations

- Tool routes are not authenticated. Anything that can reach the public URL can call them. The webhook is signed; the tools are not.
- Appointment slots are mock weekday hours, not a real clinic calendar.
- This is not a HIPAA-compliant deployment (no BAA, no encryption-at-rest review, transcripts stored in Postgres).
