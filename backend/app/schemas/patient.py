import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.models.patient import Sex
from backend.app.validation import (
    normalize_us_phone,
    parse_date_of_birth,
    validate_member_id,
    validate_person_name,
    validate_state,
    validate_zip,
)


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: EmailStr | None = None
    address_line_1: str = Field(min_length=1, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str
    zip_code: str
    insurance_provider: str | None = Field(default=None, max_length=255)
    insurance_member_id: str | None = Field(default=None, max_length=64)
    preferred_language: str = Field(default="English", min_length=1, max_length=50)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = None

    @field_validator("first_name")
    @classmethod
    def check_first_name(cls, value: str) -> str:
        return validate_person_name(value, "first_name")

    @field_validator("last_name")
    @classmethod
    def check_last_name(cls, value: str) -> str:
        return validate_person_name(value, "last_name")

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def check_dob(cls, value: Any) -> date:
        return parse_date_of_birth(value)

    @field_validator("phone_number", mode="before")
    @classmethod
    def check_phone(cls, value: str) -> str:
        return normalize_us_phone(value)

    @field_validator("email", "address_line_2", "insurance_provider", mode="before")
    @classmethod
    def blank_optional(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @field_validator("address_line_1", "city", "preferred_language")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("state")
    @classmethod
    def check_state(cls, value: str) -> str:
        return validate_state(value)

    @field_validator("zip_code")
    @classmethod
    def check_zip(cls, value: str) -> str:
        return validate_zip(value)

    @field_validator("insurance_member_id", mode="before")
    @classmethod
    def check_member_id(cls, value: Any) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        return validate_member_id(value)

    @field_validator("emergency_contact_name", mode="before")
    @classmethod
    def check_emergency_name(cls, value: Any) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        cleaned = value.strip()
        if not 1 <= len(cleaned) <= 100:
            raise ValueError("must be 1-100 characters")
        return cleaned

    @field_validator("emergency_contact_phone", mode="before")
    @classmethod
    def check_emergency_phone(cls, value: Any) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        return normalize_us_phone(value)


class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = None
    zip_code: str | None = None
    insurance_provider: str | None = Field(default=None, max_length=255)
    insurance_member_id: str | None = Field(default=None, max_length=64)
    preferred_language: str | None = Field(default=None, max_length=50)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = None

    @field_validator(
        "first_name",
        "last_name",
        "date_of_birth",
        "sex",
        "phone_number",
        "address_line_1",
        "city",
        "state",
        "zip_code",
    )
    @classmethod
    def reject_null_required(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("cannot be null")
        return value

    @field_validator("first_name")
    @classmethod
    def check_first_name(cls, value: str) -> str:
        return validate_person_name(value, "first_name")

    @field_validator("last_name")
    @classmethod
    def check_last_name(cls, value: str) -> str:
        return validate_person_name(value, "last_name")

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def check_dob(cls, value: Any) -> Any:
        if value is None:
            return None
        return parse_date_of_birth(value)

    @field_validator("phone_number", mode="before")
    @classmethod
    def check_phone(cls, value: Any) -> Any:
        if value is None:
            return None
        return normalize_us_phone(value)

    @field_validator(
        "email",
        "address_line_2",
        "insurance_provider",
        "preferred_language",
        mode="before",
    )
    @classmethod
    def blank_optional(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @field_validator("address_line_1", "city")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("cannot be blank")
        return cleaned

    @field_validator("preferred_language")
    @classmethod
    def strip_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not 1 <= len(cleaned) <= 50:
            raise ValueError("must be 1-50 characters")
        return cleaned

    @field_validator("state")
    @classmethod
    def check_state(cls, value: str) -> str:
        return validate_state(value)

    @field_validator("zip_code")
    @classmethod
    def check_zip(cls, value: str) -> str:
        return validate_zip(value)

    @field_validator("insurance_member_id", mode="before")
    @classmethod
    def check_member_id(cls, value: Any) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        return validate_member_id(value)

    @field_validator("emergency_contact_name", mode="before")
    @classmethod
    def check_emergency_name(cls, value: Any) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        cleaned = str(value).strip()
        if not 1 <= len(cleaned) <= 100:
            raise ValueError("must be 1-100 characters")
        return cleaned

    @field_validator("emergency_contact_phone", mode="before")
    @classmethod
    def check_emergency_phone(cls, value: Any) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        return normalize_us_phone(value)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: EmailStr | None
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    zip_code: str
    insurance_provider: str | None
    insurance_member_id: str | None
    preferred_language: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DeleteResult(BaseModel):
    message: str
