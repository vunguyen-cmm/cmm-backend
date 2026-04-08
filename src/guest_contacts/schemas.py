"""Pydantic schemas for guest contact submissions."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GuestContactCreate(BaseModel):
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None
    role: str | None = None
    school_name: str | None = None
    message: str


class GuestContactDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None
    role: str | None = None
    school_name: str | None = None
    message: str
    created_at: datetime | None = None
