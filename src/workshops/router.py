"""Workshop, webinar, and registration endpoints (admin + public)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.auth.deps import AdminDep
from src.db.deps import DbDep
from src.workshops.models import PortalMapping, Webinar, Workshop, WorkshopRegistration
from src.workshops.schemas import (
    RegistrationCreate,
    RegistrationOut,
    RegistrationUpdate,
    SchoolWorkshopsResponse,
    WebinarCreate,
    WebinarOut,
    WebinarSummary,
    WebinarUpdate,
    WorkshopCreate,
    WorkshopOut,
    WorkshopPortalItem,
    WorkshopSummary,
    WorkshopUpdate,
)

router = APIRouter(prefix="/api/v1/workshops", tags=["workshops"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _webinar_out(webinar: Webinar) -> WebinarOut:
    return WebinarOut(
        id=webinar.id,
        workshop_id=webinar.workshop_id,
        cohort_id=webinar.cohort_id,
        cycle_id=webinar.cycle_id,
        webinar_name=webinar.webinar_name,
        zoom_webinar_id=webinar.zoom_webinar_id,
        start_datetime=webinar.start_datetime,
        end_datetime=webinar.end_datetime,
        duration_minutes=webinar.duration_minutes,
        join_url=webinar.join_url,
        start_url=webinar.start_url,
        registration_url=webinar.registration_url,
        zoom_link=webinar.zoom_link,
        video_embed_code=webinar.video_embed_code,
        audio_transcript=webinar.audio_transcript,
        track_registrations=webinar.track_registrations,
        created_at=webinar.created_at,
        workshop_name=webinar.workshop.name,
        cohort_name=webinar.cohort.name,
        registration_count=len(webinar.registrations),
    )


def _registration_out(reg: WorkshopRegistration) -> RegistrationOut:
    return RegistrationOut(
        id=reg.id,
        webinar_id=reg.webinar_id,
        school_id=reg.school_id,
        first_name=reg.first_name,
        last_name=reg.last_name,
        full_name=reg.full_name,
        email=reg.email,
        grade=reg.grade,
        status=reg.status,
        attended=reg.attended,
        join_time=reg.join_time,
        leave_time=reg.leave_time,
        zoom_registrant_id=reg.zoom_registrant_id,
        questions=reg.questions,
        registration_time=reg.registration_time,
        created_at=reg.created_at,
        school_name=reg.school.name if reg.school else None,
    )


def _workshop_out(obj: Workshop) -> WorkshopOut:
    webinar_summaries = [
        WebinarSummary(
            id=w.id,
            webinar_name=w.webinar_name,
            cohort_id=w.cohort_id,
            start_datetime=w.start_datetime,
            end_datetime=w.end_datetime,
            zoom_webinar_id=w.zoom_webinar_id,
            registration_url=w.registration_url,
            zoom_link=w.zoom_link,
            registration_count=len(w.registrations),
        )
        for w in obj.webinars
    ]
    return WorkshopOut(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        key_actions=obj.key_actions,
        sequence_number=obj.sequence_number,
        suggested_grades=obj.suggested_grades,
        resource_center_slug=obj.resource_center_slug,
        workshop_art_url=obj.workshop_art_url,
        created_at=obj.created_at,
        webinar_count=len(obj.webinars),
        webinars=webinar_summaries,
    )


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


# ── Admin: Webinars (literal prefix — registered before /{workshop_id}) ─────


@router.get("/webinars/{webinar_id}", response_model=WebinarOut)
def get_webinar(webinar_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.execute(
        select(Webinar)
        .where(Webinar.id == webinar_id)
        .options(selectinload(Webinar.workshop), selectinload(Webinar.cohort), selectinload(Webinar.registrations))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Webinar not found")
    return _webinar_out(obj)


@router.patch("/webinars/{webinar_id}", response_model=WebinarOut)
def update_webinar(webinar_id: uuid.UUID, body: WebinarUpdate, _admin: AdminDep, db: DbDep):
    obj = db.execute(
        select(Webinar)
        .where(Webinar.id == webinar_id)
        .options(selectinload(Webinar.workshop), selectinload(Webinar.cohort), selectinload(Webinar.registrations))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Webinar not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _webinar_out(obj)


@router.delete("/webinars/{webinar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webinar(webinar_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(Webinar, webinar_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Webinar not found")
    db.delete(obj)
    db.commit()


@router.get("/webinars/{webinar_id}/registrations", response_model=list[RegistrationOut])
def list_registrations(webinar_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    webinar = db.get(Webinar, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
    regs = db.execute(
        select(WorkshopRegistration)
        .where(WorkshopRegistration.webinar_id == webinar_id)
        .options(selectinload(WorkshopRegistration.school))
        .order_by(WorkshopRegistration.created_at)
    ).scalars().all()
    return [_registration_out(r) for r in regs]


@router.post("/webinars/{webinar_id}/registrations", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED)
def create_registration(webinar_id: uuid.UUID, body: RegistrationCreate, _admin: AdminDep, db: DbDep):
    webinar = db.get(Webinar, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
    if body.webinar_id != webinar_id:
        raise HTTPException(status_code=400, detail="webinar_id in body must match URL")
    obj = WorkshopRegistration(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    obj = db.execute(
        select(WorkshopRegistration)
        .where(WorkshopRegistration.id == obj.id)
        .options(selectinload(WorkshopRegistration.school))
    ).scalar_one()
    return _registration_out(obj)


# ── Admin: Registrations (literal prefix) ────────────────────────────────────


@router.patch("/registrations/{registration_id}", response_model=RegistrationOut)
def update_registration(registration_id: uuid.UUID, body: RegistrationUpdate, _admin: AdminDep, db: DbDep):
    obj = db.execute(
        select(WorkshopRegistration)
        .where(WorkshopRegistration.id == registration_id)
        .options(selectinload(WorkshopRegistration.school))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Registration not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _registration_out(obj)


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registration(registration_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(WorkshopRegistration, registration_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Registration not found")
    db.delete(obj)
    db.commit()


# ── Public endpoints (literal prefix) ───────────────────────────────────────


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


# ── Admin: Workshops (parameterised paths — registered last) ─────────────────


@router.get("/", response_model=list[WorkshopSummary])
def list_workshops(_admin: AdminDep, db: DbDep):
    """Admin: list all workshops with webinar counts and next upcoming date."""
    now = datetime.now(tz=timezone.utc)

    webinar_count_sq = (
        select(func.count(Webinar.id))
        .where(Webinar.workshop_id == Workshop.id)
        .correlate(Workshop)
        .scalar_subquery()
    )
    next_webinar_sq = (
        select(func.min(Webinar.start_datetime))
        .where(Webinar.workshop_id == Workshop.id, Webinar.start_datetime >= now)
        .correlate(Workshop)
        .scalar_subquery()
    )

    stmt = (
        select(
            Workshop,
            webinar_count_sq.label("webinar_count"),
            next_webinar_sq.label("next_webinar_date"),
        )
        .order_by(Workshop.sequence_number.nulls_last(), Workshop.name)
    )

    rows = db.execute(stmt).all()
    return [
        WorkshopSummary(
            id=row.Workshop.id,
            name=row.Workshop.name,
            description=row.Workshop.description,
            suggested_grades=row.Workshop.suggested_grades,
            workshop_art_url=row.Workshop.workshop_art_url,
            sequence_number=row.Workshop.sequence_number,
            created_at=row.Workshop.created_at,
            webinar_count=row.webinar_count,
            next_webinar_date=row.next_webinar_date,
        )
        for row in rows
    ]


@router.post("/", response_model=WorkshopOut, status_code=status.HTTP_201_CREATED)
def create_workshop(body: WorkshopCreate, _admin: AdminDep, db: DbDep):
    obj = Workshop(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return WorkshopOut(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        key_actions=obj.key_actions,
        sequence_number=obj.sequence_number,
        suggested_grades=obj.suggested_grades,
        resource_center_slug=obj.resource_center_slug,
        workshop_art_url=obj.workshop_art_url,
        created_at=obj.created_at,
        webinar_count=0,
        webinars=[],
    )


@router.get("/{workshop_id}", response_model=WorkshopOut)
def get_workshop(workshop_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    """Admin: get workshop detail with webinars."""
    obj = db.execute(
        select(Workshop)
        .where(Workshop.id == workshop_id)
        .options(selectinload(Workshop.webinars).selectinload(Webinar.registrations))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return _workshop_out(obj)


@router.patch("/{workshop_id}", response_model=WorkshopOut)
def update_workshop(workshop_id: uuid.UUID, body: WorkshopUpdate, _admin: AdminDep, db: DbDep):
    obj = db.execute(
        select(Workshop)
        .where(Workshop.id == workshop_id)
        .options(selectinload(Workshop.webinars).selectinload(Webinar.registrations))
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Workshop not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _workshop_out(obj)


@router.delete("/{workshop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workshop(workshop_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(Workshop, workshop_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Workshop not found")
    db.delete(obj)
    db.commit()


@router.post("/{workshop_id}/webinars", response_model=WebinarOut, status_code=status.HTTP_201_CREATED)
def create_webinar(workshop_id: uuid.UUID, body: WebinarCreate, _admin: AdminDep, db: DbDep):
    workshop = db.get(Workshop, workshop_id)
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if body.workshop_id != workshop_id:
        raise HTTPException(status_code=400, detail="workshop_id in body must match URL")
    obj = Webinar(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    # Eager-load relationships for the response
    obj = db.execute(
        select(Webinar)
        .where(Webinar.id == obj.id)
        .options(selectinload(Webinar.workshop), selectinload(Webinar.cohort), selectinload(Webinar.registrations))
    ).scalar_one()
    return _webinar_out(obj)
