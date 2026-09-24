import re
from datetime import date, datetime, timezone

US_STATE_ABBREVIATIONS = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "VI", "GU", "AS", "MP",
    }
)

NAME_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
ZIP_RE = re.compile(r"\d{5}(?:-\d{4})?")
MEMBER_ID_RE = re.compile(r"[A-Za-z0-9]+")


def validate_person_name(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not NAME_RE.fullmatch(cleaned) or not 1 <= len(cleaned) <= 50:
        raise ValueError(
            f"{field_name} must be 1-50 characters and contain only letters, hyphens, and apostrophes"
        )
    return cleaned


def normalize_us_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value.strip())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError("must be a valid U.S. 10-digit phone number")
    return digits


def parse_date_of_birth(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        parsed = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError("must be a valid date in YYYY-MM-DD or MM/DD/YYYY format")
    else:
        raise ValueError("must be a valid date in YYYY-MM-DD or MM/DD/YYYY format")

    if parsed > datetime.now(timezone.utc).date():
        raise ValueError("cannot be in the future")
    return parsed


def validate_state(value: str) -> str:
    code = value.strip().upper()
    if code not in US_STATE_ABBREVIATIONS:
        raise ValueError("must be a valid 2-letter U.S. state abbreviation")
    return code


def validate_zip(value: str) -> str:
    cleaned = value.strip()
    if not ZIP_RE.fullmatch(cleaned):
        raise ValueError("must be a 5-digit or ZIP+4 code (12345 or 12345-6789)")
    return cleaned


def validate_member_id(value: str) -> str:
    cleaned = value.strip()
    if not MEMBER_ID_RE.fullmatch(cleaned):
        raise ValueError("must be alphanumeric")
    return cleaned
