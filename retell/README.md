# Retell Voice Intake Agent

Conversational patient intake on Retell AI. The agent collects details over the phone and writes them through the Patient Registration API.

## Resource IDs

| Resource | ID |
|---|---|
| Agent | `agent_cef430473eb97beb8523e434bf` |
| Response engine (Retell LLM) | `llm_399dc8cd548f15a8b34abb506a32` |
| Agent name | CareCloud Patient Intake |
| Channel | voice |
| Language | `multi` (English by default; Spanish when the caller switches) |
| Voice | `11labs-Brian` (multilingual) |
| Model | Retell default (`gpt-5.6-terra`) |
| Phone number | `+1 (413) 848-7102` (`+14138487102`), inbound agent bound |
| Webhook | `https://api-production-57f92.up.railway.app/retell/webhook` |

Agent type: **Single/Multi-Prompt** (one `general_prompt`), not a Conversation Flow.

Version history:

- v1 batched questions (name together; DOB + sex together; whole address at once), stopped echoing every answer, and used one concise read-back before saving.
- v2 added out-of-order / volunteered info, interruptions, and a graceful start-over.
- v3 named the coordinator Huzaifa Tanzeel, switched the voice to `11labs-Brian`, and set the opening line.
- Next published version points `create_patient` at `/retell/tools/create_patient` (`args_at_root: false`), adds lookup, update, slots, and booking, stores transcripts via the webhook, and turns on Spanish.

Begin message (spoken first by the agent):

> Hi, this is Huzaifa Tanzeel with patient registration. I'll get you set up in just a couple of minutes. To get started, could I grab your full name?

The agent sends dates as `YYYY-MM-DD`. The challenge PDF lists `MM/DD/YYYY`; the API accepts both, and `YYYY-MM-DD` avoids day/month ambiguity for the model.

## Files

- [`system_prompt.md`](system_prompt.md) — `general_prompt`.
- [`create_patient_function.json`](create_patient_function.json) — save a new patient after confirmation.
- [`lookup_patient_function.json`](lookup_patient_function.json) — returning-caller check by phone.
- [`update_patient_function.json`](update_patient_function.json) — partial update for a known `patient_id`.
- [`get_available_slots_function.json`](get_available_slots_function.json) — next mock openings.
- [`book_appointment_function.json`](book_appointment_function.json) — book a chosen slot.

Every custom tool is `POST` with `args_at_root: false`, so the body is `{ "call": {...}, "name": "...", "args": {...} }`. `create_patient` uses `timeout_ms: 30000` to cover a cold start. `speak_during_execution` is on for writes and off for the quiet lookup.

## How to test (browser)

1. Retell dashboard → Agents → **CareCloud Patient Intake** → **Test**. Allow the microphone.
2. Register out loud: name, phone (the agent looks this up immediately), date of birth and sex, then the address.
3. Confirm it offers insurance, emergency contact, and language once, and does not insist.
4. Correct one field mid-call and confirm it does not restart.
5. Give a future date of birth or a bad state and confirm it re-asks only that field.
6. Say yes only after the single read-back. It should save, offer a first appointment, and close with your first name.
7. Call again with the same phone number. It should offer to update instead of creating a duplicate.
8. Say a sentence in Spanish and confirm it stays in Spanish.

A confirmed call writes a real row in the Railway database. Use obvious test data. Check `/dashboard`, and soft-delete with `DELETE /patients/{patient_id}` if you need to clean up.
