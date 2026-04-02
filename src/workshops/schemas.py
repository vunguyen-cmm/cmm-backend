"""Public schemas for workshops portal endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorkshopPortalItem(BaseModel):
    """A webinar+workshop merged for the school portal."""

    model_config = ConfigDict(from_attributes=True)

    # Webinar fields
    webinar_id: uuid.UUID
    start_datetime: datetime | None
    end_datetime: datetime | None
    registration_url: str | None
    zoom_link: str | None
    video_embed_code: str | None
    join_url: str | None
    show_zoom: bool

    # Workshop fields
    workshop_id: uuid.UUID
    name: str
    description: str | None
    key_actions: str | None
    suggested_grades: str | None
    workshop_art_url: str | None
    sequence_number: int | None


class SchoolWorkshopsResponse(BaseModel):
    upcoming: list[WorkshopPortalItem]
    past: list[WorkshopPortalItem]
