import enum
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base
from backend.app.validation import US_STATE_ABBREVIATIONS

_STATE_LIST = ", ".join(f"'{code}'" for code in sorted(US_STATE_ABBREVIATIONS))


class Sex(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE_TO_ANSWER = "Decline to Answer"


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(
            r"first_name ~ '^[A-Za-z]+([''-][A-Za-z]+)*$' AND char_length(first_name) <= 50",
            name="ck_patients_first_name",
        ),
        CheckConstraint(
            r"last_name ~ '^[A-Za-z]+([''-][A-Za-z]+)*$' AND char_length(last_name) <= 50",
            name="ck_patients_last_name",
        ),
        CheckConstraint("date_of_birth <= CURRENT_DATE", name="ck_patients_date_of_birth"),
        CheckConstraint("phone_number ~ '^[0-9]{10}$'", name="ck_patients_phone_number"),
        CheckConstraint(
            "char_length(city) BETWEEN 1 AND 100",
            name="ck_patients_city",
        ),
        CheckConstraint(f"state IN ({_STATE_LIST})", name="ck_patients_state"),
        CheckConstraint(
            r"zip_code ~ '^[0-9]{5}(-[0-9]{4})?$'",
            name="ck_patients_zip_code",
        ),
        CheckConstraint(
            "insurance_member_id IS NULL OR insurance_member_id ~ '^[A-Za-z0-9]+$'",
            name="ck_patients_insurance_member_id",
        ),
        CheckConstraint(
            "emergency_contact_phone IS NULL OR emergency_contact_phone ~ '^[0-9]{10}$'",
            name="ck_patients_emergency_contact_phone",
        ),
        CheckConstraint(
            "char_length(address_line_1) >= 1",
            name="ck_patients_address_line_1",
        ),
        Index("ix_patients_last_name_date_of_birth", "last_name", "date_of_birth"),
        Index("ix_patients_phone_number", "phone_number"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    sex: Mapped[Sex] = mapped_column(
        Enum(
            Sex,
            name="patient_sex",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(String(10), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    insurance_provider: Mapped[str | None] = mapped_column(String(255))
    insurance_member_id: Mapped[str | None] = mapped_column(String(64))
    preferred_language: Mapped[str | None] = mapped_column(
        String(50), server_default=text("'English'")
    )
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
