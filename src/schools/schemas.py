"""Pydantic schemas for schools — aligned with SQLAlchemy models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CohortSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ContactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    receive_comms: bool = True


class SchoolListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    enrollment_9_12: int | None = None
    enrollment_range: str | None = None
    is_current_customer: bool = False
    logo_url: str | None = None
    logo_thumb_url: str | None = None
    slug: str | None = None
    cohort_id: uuid.UUID | None = None
    cohort: CohortSummary | None = None
    created_at: datetime | None = None
    # Link fields (hidden columns in admin table)
    school_resource_center_url: str | None = None
    appointlet_link: str | None = None
    calendar_link: str | None = None
    bubble_rec_id: str | None = None


class SchoolDetail(SchoolListItem):
    street_address: str | None = None
    cmm_website_password: str | None = None
    school_resource_center_url: str | None = None
    appointlet_link: str | None = None
    calendar_link: str | None = None
    bubble_rec_id: str | None = None
    contacts: list[ContactSummary] = []


class SchoolCreate(BaseModel):
    name: str
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    street_address: str | None = None
    enrollment_9_12: int | None = None
    cohort_id: uuid.UUID | None = None
    is_current_customer: bool = False
    logo_url: str | None = None
    school_resource_center_url: str | None = None
    appointlet_link: str | None = None
    calendar_link: str | None = None
    cmm_website_password: str | None = None


class SchoolUpdate(BaseModel):
    """All fields optional — PATCH semantics."""

    name: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    street_address: str | None = None
    enrollment_9_12: int | None = None
    cohort_id: uuid.UUID | None = None
    is_current_customer: bool | None = None
    logo_url: str | None = None
    cmm_website_password: str | None = None
    school_resource_center_url: str | None = None
    appointlet_link: str | None = None
    calendar_link: str | None = None


class SchoolPasswordUpdate(BaseModel):
    password: str


class SchoolListResponse(BaseModel):
    items: list[SchoolListItem]
    total: int
    skip: int
    limit: int
