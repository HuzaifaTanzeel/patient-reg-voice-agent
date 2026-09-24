# Retell Voice Intake Agent

A conversational patient-intake voice agent built on Retell AI. It collects patient
details over the phone and saves them to the live Patient Registration API via one
custom function.

## Resource IDs

| Resource | ID |
|---|---|
| Agent | `agent_cef430473eb97beb8523e434bf` |
| Response engine (Retell LLM) | `llm_399dc8cd548f15a8b34abb506a32` |
| Agent name | CareCloud Patient Intake |
| Channel | voice |
| Language | en-US |
| Voice | `11labs-Marissa` (warm American female) |
| Model | Retell default (`gpt-5.6-terra`) |
| Published | yes (draft version 0, no phone number attached) |

Agent type: **Single/Multi-Prompt** (Retell LLM response engine with a single
`general_prompt`), not a Conversation Flow.

## Files
- [`system_prompt.md`](system_prompt.md) - the agent's `general_prompt`.
- [`create_patient_function.json`](create_patient_function.json) - the one custom
  function defined on the agent.

## create_patient function

- Method/URL: `POST https://api-production-57f92.up.railway.app/patients`
- `args_at_root: true` - the JSON body is sent at the root so it matches the API's
  `PatientCreate` schema exactly (the API sets `additionalProperties: false` and
  expects no `args` wrapper).
- `timeout_ms: 30000` - covers Railway cold starts.
- `speak_during_execution` / `speak_after_execution: true` - the agent reassures the
  caller while saving and responds based on the result.

### Field mapping (matches the FastAPI Pydantic schema)
- Required: `first_name`, `last_name`, `date_of_birth` (YYYY-MM-DD, past date),
  `sex` (`Male` | `Female` | `Other` | `Decline to Answer`), `phone_number`
  (10-digit US), `address_line_1`, `city`, `state` (2-letter US abbr), `zip_code`
  (5-digit / ZIP+4).
- Optional: `address_line_2`, `email`, `insurance_provider`, `insurance_member_id`,
  `preferred_language` (defaults to English), `emergency_contact_name`,
  `emergency_contact_phone`.

## How to test via Retell web (browser) test call

1. Open the Retell dashboard -> Agents -> **CareCloud Patient Intake**.
2. Click the **Test** (browser web call) button and allow microphone access.
3. Walk through a full registration out loud: name, date of birth, sex, phone,
   then street address / city / state / ZIP.
4. Confirm the agent then offers optional info (insurance, emergency contact,
   preferred language) without forcing it.
5. Try a mid-call correction (e.g. re-spell your last name) and confirm it fixes
   only that field without restarting.
6. Try an invalid value (a future date of birth, or "Californiaa" as the state) and
   confirm it re-prompts only for that field.
7. Confirm the agent reads back ALL details and only saves after you explicitly say
   "yes, that's correct."
8. On success it confirms using your first name and ends the call.

Note: a confirmed call writes a REAL row to the live Railway Postgres via
`POST /patients`. Use obvious test data. Verify with `GET /patients`, and clean up
later with `DELETE /patients/{patient_id}` if desired.

Only attach/buy a phone number after the web test looks good (out of scope here).
