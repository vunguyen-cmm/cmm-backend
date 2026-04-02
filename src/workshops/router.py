"""Public workshop endpoints for the school portal."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.deps import DbDep
from src.workshops.models import PortalMapping, Webinar, Workshop
from src.workshops.schemas import SchoolWorkshopsResponse, WorkshopPortalItem

router = APIRouter(prefix="/api/v1/workshops", tags=["workshops"])


def _to_item(mapping: PortalMapping) -> WorkshopPortalItem:
    webinar: Webinar = mapping.webinar
    workshop: Workshop = webinar.workshop
    return WorkshopPortalItem(
        webinar_id=webinar.id,
        start_datetime=webinar.start_datetime,
        end_datetime=webinar.end_datetime,
        registration_url=webinar.registration_url,
        zoom_link=webinar.zoom_link,
        video_embed_code=webinar.video_embed_code,
        join_url=webinar.join_url,
        show_zoom=mapping.show_zoom,
        workshop_id=workshop.id,
        name=workshop.name,
        description=workshop.description,
        key_actions=workshop.key_actions,
        suggested_grades=workshop.suggested_grades,
        workshop_art_url=workshop.workshop_art_url,
        sequence_number=workshop.sequence_number,
    )


@router.get("/public/school/{school_id}", response_model=SchoolWorkshopsResponse)
def get_school_workshops(school_id: uuid.UUID, db: DbDep) -> SchoolWorkshopsResponse:
    """Return upcoming and past workshops for a school portal (no auth)."""
    mappings = (
        db.execute(
            select(PortalMapping)
            .where(PortalMapping.school_id == school_id)
            .options(
                selectinload(PortalMapping.webinar).selectinload(Webinar.workshop)
            )
            .order_by(PortalMapping.created_at)
        )
        .scalars()
        .all()
    )

    now = datetime.now(tz=timezone.utc)
    upcoming: list[WorkshopPortalItem] = []
    past: list[WorkshopPortalItem] = []

    for mapping in mappings:
        item = _to_item(mapping)
        if item.start_datetime is None or item.start_datetime >= now:
            upcoming.append(item)
        else:
            past.append(item)

    # Sort upcoming ascending (soonest first), past descending (most recent first)
    upcoming.sort(key=lambda x: x.start_datetime or datetime.max.replace(tzinfo=timezone.utc))
    past.sort(key=lambda x: x.start_datetime or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    return SchoolWorkshopsResponse(upcoming=upcoming, past=past)


@router.get("/public/school/{school_id}/webinar/{webinar_id}", response_model=WorkshopPortalItem)
def get_school_webinar(school_id: uuid.UUID, webinar_id: uuid.UUID, db: DbDep) -> WorkshopPortalItem:
    """Return a single webinar's portal details for a school (no auth)."""
    mapping = (
        db.execute(
            select(PortalMapping)
            .where(
                PortalMapping.school_id == school_id,
                PortalMapping.webinar_id == webinar_id,
            )
            .options(
                selectinload(PortalMapping.webinar).selectinload(Webinar.workshop)
            )
        )
        .scalar_one_or_none()
    )
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop not found")
    return _to_item(mapping)
