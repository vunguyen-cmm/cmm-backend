"""SQLAlchemy model for Paul Martin calendar events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Text, Uuid
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.base import Base


class PaulMartinCalendar(Base):
    __tablename__ = "paul_martin_calendar"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(Text)
    start_datetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    end_datetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    google_event_id: Mapped[str | None] = mapped_column(Text, unique=True)
    event_link: Mapped[str | None] = mapped_column(Text)
    hangouts_link: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    creator: Mapped[str | None] = mapped_column(Text)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    google_updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
