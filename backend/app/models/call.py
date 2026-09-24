import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Call(Base):
    """A phone/web call handled by the Retell agent.

    Rows are created when the agent invokes a tool (linking the call to the
    patient it created/updated) and enriched by the Retell webhook once the call
    ends (transcript, summary, disconnection reason). A row with no patient_id and
    a disconnection_reason is the trace of a dropped/abandoned call.
    """

    __tablename__ = "calls"

    call_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    from_number: Mapped[str | None] = mapped_column(String(32))
    to_number: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    disconnection_reason: Mapped[str | None] = mapped_column(String(64))
    transcript: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
