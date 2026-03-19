"""Cohorts CRUD endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func

from src.auth.deps import AdminDep, CurrentUserDep
from src.cycles.models import Cohort
from src.cycles.schemas import CohortCreate, CohortOut, CohortUpdate
from src.db.deps import DbDep
from src.schools.models import School

router = APIRouter(prefix="/api/v1/cohorts", tags=["cohorts"])


@router.get("", response_model=list[CohortOut])
def list_cohorts(db: DbDep, user: CurrentUserDep) -> list[CohortOut]:
    """List all cohorts with school counts."""
    cohorts = db.query(Cohort).order_by(Cohort.name).all()
    # Build school count map
    school_counts = dict(
        db.query(School.cohort_id, func.count(School.id))
        .filter(School.cohort_id.isnot(None))
        .group_by(School.cohort_id)
        .all()
    )
    results = []
    for cohort in cohorts:
        out = CohortOut.model_validate(cohort)
        out.school_count = school_counts.get(cohort.id, 0)
        results.append(out)
    return results


@router.post("", response_model=CohortOut, status_code=status.HTTP_201_CREATED)
def create_cohort(body: CohortCreate, _admin: AdminDep, db: DbDep) -> CohortOut:
    """Create a cohort (admin only)."""
    existing = db.query(Cohort).filter(Cohort.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="A cohort with this name already exists")
    cohort = Cohort(**body.model_dump())
    db.add(cohort)
    db.commit()
    db.refresh(cohort)
    out = CohortOut.model_validate(cohort)
    out.school_count = 0
    return out


@router.patch("/{cohort_id}", response_model=CohortOut)
def update_cohort(
    cohort_id: uuid.UUID,
    body: CohortUpdate,
    _admin: AdminDep,
    db: DbDep,
) -> CohortOut:
    """Update a cohort (admin only)."""
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data:
        dup = (
            db.query(Cohort)
            .filter(Cohort.name == update_data["name"], Cohort.id != cohort_id)
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail="A cohort with this name already exists")

    for field, value in update_data.items():
        setattr(cohort, field, value)

    db.commit()
    db.refresh(cohort)

    count = db.query(func.count(School.id)).filter(School.cohort_id == cohort_id).scalar() or 0
    out = CohortOut.model_validate(cohort)
    out.school_count = count
    return out


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cohort(cohort_id: uuid.UUID, _admin: AdminDep, db: DbDep) -> None:
    """Delete a cohort (admin only). Schools in this cohort will have cohort_id set to NULL."""
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    # Nullify school cohort references before deleting
    db.query(School).filter(School.cohort_id == cohort_id).update(
        {School.cohort_id: None}, synchronize_session=False
    )
    db.delete(cohort)
    db.commit()
