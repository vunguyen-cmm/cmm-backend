"""FastAPI router for guest contact submissions."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from src.auth.deps import AdminDep
from src.db.deps import DbDep
from src.guest_contacts.models import GuestContact
from src.guest_contacts.schemas import GuestContactCreate, GuestContactDetail

router = APIRouter(prefix="/api/v1/guest-contacts", tags=["guest-contacts"])


# ── Public endpoint (no auth) ───────────────────────────────────────

@router.post("", response_model=GuestContactDetail, status_code=status.HTTP_201_CREATED)
def submit_guest_contact(body: GuestContactCreate, db: DbDep):
    """Public endpoint — guests submit contact info from the website."""
    gc = GuestContact(**body.model_dump(exclude_none=True))
    db.add(gc)
    db.commit()
    db.refresh(gc)
    return GuestContactDetail.model_validate(gc)


# ── Admin endpoints ──────────────────────────────────────────────────

@router.get("", response_model=list[GuestContactDetail])
def list_guest_contacts(
    db: DbDep,
    _admin: AdminDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List all guest contact submissions (admin only)."""
    rows = (
        db.query(GuestContact)
        .order_by(GuestContact.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [GuestContactDetail.model_validate(r) for r in rows]


@router.get("/{gc_id}", response_model=GuestContactDetail)
def get_guest_contact(gc_id: uuid.UUID, db: DbDep, _admin: AdminDep):
    """Get a single guest contact by ID (admin only)."""
    gc = db.query(GuestContact).filter(GuestContact.id == gc_id).first()
    if not gc:
        raise HTTPException(status_code=404, detail="Guest contact not found")
    return GuestContactDetail.model_validate(gc)


@router.delete("/{gc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guest_contact(gc_id: uuid.UUID, db: DbDep, _admin: AdminDep):
    """Delete a guest contact (admin only)."""
    gc = db.query(GuestContact).filter(GuestContact.id == gc_id).first()
    if not gc:
        raise HTTPException(status_code=404, detail="Guest contact not found")
    db.delete(gc)
    db.commit()
