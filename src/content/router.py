"""Content management API router."""

from __future__ import annotations

import io
import uuid
from typing import Annotated

import boto3
import requests
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.auth.deps import AdminDep
from src.content.models import (
    AssetType,
    ContentAsset,
    ContentAssetCohort,
    ContentAssetFaq,
    ContentAssetObjective,
    ContentAssetResource,
    ContentAssetTopic,
    ContentAssetWorkshop,
    Faq,
    Objective,
    ReaderQuestion,
    Topic,
)
from src.content.schemas import (
    AssetTypeCreate,
    AssetTypeOut,
    AssetTypeUpdate,
    ContentAssetCreate,
    ContentAssetDetail,
    ContentAssetListItem,
    ContentAssetListResponse,
    ContentAssetUpdate,
    FaqCreate,
    FaqOut,
    FaqsUpdate,
    FaqUpdate,
    ObjectiveCreate,
    ObjectiveOut,
    ObjectiveUpdate,
    ReaderQuestionCreate,
    ReaderQuestionOut,
    RelationshipsUpdate,
    ResourcesUpdate,
    TopicCreate,
    TopicOut,
    TopicUpdate,
)
from src.config import settings
from src.db.deps import DbDep

router = APIRouter(prefix="/api/v1/content", tags=["content"])

# ── Asset Types ───────────────────────────────────────────────────────────────

@router.get("/asset-types", response_model=list[AssetTypeOut])
def list_asset_types(db: DbDep):
    return db.scalars(select(AssetType).order_by(AssetType.name)).all()


@router.post("/asset-types", response_model=AssetTypeOut, status_code=status.HTTP_201_CREATED)
def create_asset_type(body: AssetTypeCreate, _admin: AdminDep, db: DbDep):
    existing = db.scalar(select(AssetType).where(AssetType.name == body.name))
    if existing:
        raise HTTPException(status_code=409, detail="Asset type with this name already exists")
    obj = AssetType(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/asset-types/{asset_type_id}", response_model=AssetTypeOut)
def update_asset_type(asset_type_id: uuid.UUID, body: AssetTypeUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(AssetType, asset_type_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Asset type not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/asset-types/{asset_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_type(asset_type_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(AssetType, asset_type_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Asset type not found")
    db.delete(obj)
    db.commit()


# ── Topics ────────────────────────────────────────────────────────────────────

@router.get("/topics", response_model=list[TopicOut])
def list_topics(db: DbDep):
    return db.scalars(select(Topic).order_by(Topic.name)).all()


@router.post("/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(body: TopicCreate, _admin: AdminDep, db: DbDep):
    existing = db.scalar(select(Topic).where(Topic.name == body.name))
    if existing:
        raise HTTPException(status_code=409, detail="Topic with this name already exists")
    obj = Topic(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: uuid.UUID, body: TopicUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(Topic, topic_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Topic not found")
    obj.name = body.name
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(Topic, topic_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(obj)
    db.commit()


# ── Objectives ────────────────────────────────────────────────────────────────

@router.get("/objectives", response_model=list[ObjectiveOut])
def list_objectives(db: DbDep):
    return db.scalars(select(Objective).order_by(Objective.name)).all()


@router.post("/objectives", response_model=ObjectiveOut, status_code=status.HTTP_201_CREATED)
def create_objective(body: ObjectiveCreate, _admin: AdminDep, db: DbDep):
    obj = Objective(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/objectives/{objective_id}", response_model=ObjectiveOut)
def update_objective(objective_id: uuid.UUID, body: ObjectiveUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(Objective, objective_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/objectives/{objective_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_objective(objective_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(Objective, objective_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    db.delete(obj)
    db.commit()


# ── Content Assets ────────────────────────────────────────────────────────────

def _load_asset_detail(db: DbDep, asset_id: uuid.UUID) -> ContentAsset:
    stmt = (
        select(ContentAsset)
        .where(ContentAsset.id == asset_id)
        .options(
            selectinload(ContentAsset.asset_type),
            selectinload(ContentAsset.objectives),
            selectinload(ContentAsset.topics),
            selectinload(ContentAsset.workshops),
            selectinload(ContentAsset.cohorts),
            selectinload(ContentAsset.faqs),
            selectinload(ContentAsset.resources).selectinload(ContentAsset.asset_type),
        )
    )
    obj = db.scalar(stmt)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    return obj


def _resolve_resources(db: DbDep, asset: ContentAsset) -> list[ContentAsset]:
    """Return hand-picked resources or auto-fallback by shared objectives/topics."""
    if asset.resources:
        return list(asset.resources)

    obj_ids = [o.id for o in asset.objectives]
    topic_ids = [t.id for t in asset.topics]
    if not obj_ids and not topic_ids:
        return []

    from src.content.models import ContentAssetObjective as CAO, ContentAssetTopic as CAT

    subq_obj = select(CAO.content_asset_id).where(CAO.objective_id.in_(obj_ids))
    subq_top = select(CAT.content_asset_id).where(CAT.topic_id.in_(topic_ids))
    stmt = (
        select(ContentAsset)
        .options(selectinload(ContentAsset.asset_type))
        .where(
            ContentAsset.status == "published",
            ContentAsset.id != asset.id,
            or_(
                ContentAsset.id.in_(subq_obj),
                ContentAsset.id.in_(subq_top),
            ),
        )
        .limit(6)
    )
    return list(db.scalars(stmt).all())


@router.get("/assets", response_model=ContentAssetListResponse)
def list_assets(
    db: DbDep,
    search: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    asset_type_id: Annotated[uuid.UUID | None, Query()] = None,
    objective_id: Annotated[uuid.UUID | None, Query()] = None,
    topic_id: Annotated[uuid.UUID | None, Query()] = None,
    cohort_id: Annotated[uuid.UUID | None, Query()] = None,
    is_featured: Annotated[bool | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_dir: Annotated[str, Query()] = "desc",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    stmt = select(ContentAsset).options(selectinload(ContentAsset.asset_type))

    if search:
        stmt = stmt.where(ContentAsset.name.ilike(f"%{search}%"))
    if status:
        stmt = stmt.where(ContentAsset.status == status)
    if asset_type_id:
        stmt = stmt.where(ContentAsset.asset_type_id == asset_type_id)
    if is_featured is not None:
        stmt = stmt.where(ContentAsset.is_featured == is_featured)
    if objective_id:
        stmt = stmt.join(ContentAssetObjective).where(ContentAssetObjective.objective_id == objective_id)
    if topic_id:
        stmt = stmt.join(ContentAssetTopic).where(ContentAssetTopic.topic_id == topic_id)
    if cohort_id:
        stmt = stmt.join(ContentAssetCohort).where(ContentAssetCohort.cohort_id == cohort_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt)

    sort_col = getattr(ContentAsset, sort_by, ContentAsset.created_at)
    if sort_dir == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    items = db.scalars(stmt.offset(skip).limit(limit)).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/assets/{asset_id}/public", response_model=ContentAssetDetail)
def get_asset_public(asset_id: uuid.UUID, db: DbDep):
    """Public endpoint — only returns published assets."""
    asset = _load_asset_detail(db, asset_id)
    if asset.status != "published":
        raise HTTPException(status_code=404, detail="Content asset not found")
    asset.resources = _resolve_resources(db, asset)
    return asset


@router.get("/assets/{asset_id}", response_model=ContentAssetDetail)
def get_asset(asset_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    asset = _load_asset_detail(db, asset_id)
    asset.resources = _resolve_resources(db, asset)
    return asset


@router.post("/assets", response_model=ContentAssetDetail, status_code=status.HTTP_201_CREATED)
def create_asset(_admin: AdminDep, body: ContentAssetCreate, db: DbDep):
    obj = ContentAsset(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _load_asset_detail(db, obj.id)


@router.patch("/assets/{asset_id}", response_model=ContentAssetDetail)
def update_asset(asset_id: uuid.UUID, body: ContentAssetUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.delete(obj)
    db.commit()


@router.patch("/assets/{asset_id}/publish", response_model=ContentAssetDetail)
def publish_asset(asset_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    obj.status = "published"
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.patch("/assets/{asset_id}/unpublish", response_model=ContentAssetDetail)
def unpublish_asset(asset_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    obj.status = "draft"
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.post("/assets/{asset_id}/image", response_model=ContentAssetDetail)
async def upload_asset_image(asset_id: uuid.UUID, file: UploadFile, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "bin")
    s3_key = f"assets/content/{asset_id}/image.{ext}"

    data = await file.read()
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )
    s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=s3_key,
        Body=data,
        ContentType=file.content_type,
    )
    obj.image_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
    db.commit()
    return _load_asset_detail(db, asset_id)


# ── Relationship management ───────────────────────────────────────────────────

@router.put("/assets/{asset_id}/objectives", response_model=ContentAssetDetail)
def update_asset_objectives(asset_id: uuid.UUID, body: RelationshipsUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.query(ContentAssetObjective).filter_by(content_asset_id=asset_id).delete()
    for oid in body.ids:
        db.add(ContentAssetObjective(content_asset_id=asset_id, objective_id=oid))
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.put("/assets/{asset_id}/topics", response_model=ContentAssetDetail)
def update_asset_topics(asset_id: uuid.UUID, body: RelationshipsUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.query(ContentAssetTopic).filter_by(content_asset_id=asset_id).delete()
    for tid in body.ids:
        db.add(ContentAssetTopic(content_asset_id=asset_id, topic_id=tid))
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.put("/assets/{asset_id}/workshops", response_model=ContentAssetDetail)
def update_asset_workshops(asset_id: uuid.UUID, body: RelationshipsUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.query(ContentAssetWorkshop).filter_by(content_asset_id=asset_id).delete()
    for wid in body.ids:
        db.add(ContentAssetWorkshop(content_asset_id=asset_id, workshop_id=wid))
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.put("/assets/{asset_id}/cohorts", response_model=ContentAssetDetail)
def update_asset_cohorts(asset_id: uuid.UUID, body: RelationshipsUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.query(ContentAssetCohort).filter_by(content_asset_id=asset_id).delete()
    for cid in body.ids:
        db.add(ContentAssetCohort(content_asset_id=asset_id, cohort_id=cid))
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.put("/assets/{asset_id}/faqs", response_model=ContentAssetDetail)
def update_asset_faqs(asset_id: uuid.UUID, body: FaqsUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.query(ContentAssetFaq).filter_by(content_asset_id=asset_id).delete()
    for item in body.items:
        db.add(ContentAssetFaq(content_asset_id=asset_id, faq_id=item.faq_id, sort_order=item.sort_order))
    db.commit()
    return _load_asset_detail(db, asset_id)


@router.put("/assets/{asset_id}/resources", response_model=ContentAssetDetail)
def update_asset_resources(asset_id: uuid.UUID, body: ResourcesUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(ContentAsset, asset_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Content asset not found")
    db.query(ContentAssetResource).filter_by(content_asset_id=asset_id).delete()
    for item in body.items:
        db.add(ContentAssetResource(content_asset_id=asset_id, resource_id=item.resource_id, sort_order=item.sort_order))
    db.commit()
    asset = _load_asset_detail(db, asset_id)
    asset.resources = _resolve_resources(db, asset)
    return asset


# ── FAQs ──────────────────────────────────────────────────────────────────────

@router.get("/faqs", response_model=list[FaqOut])
def list_faqs(_admin: AdminDep, db: DbDep):
    return db.scalars(select(Faq).order_by(Faq.created_at.desc())).all()


@router.post("/faqs", response_model=FaqOut, status_code=status.HTTP_201_CREATED)
def create_faq(body: FaqCreate, _admin: AdminDep, db: DbDep):
    obj = Faq(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/faqs/{faq_id}", response_model=FaqOut)
def update_faq(faq_id: uuid.UUID, body: FaqUpdate, _admin: AdminDep, db: DbDep):
    obj = db.get(Faq, faq_id)
    if not obj:
        raise HTTPException(status_code=404, detail="FAQ not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faq(faq_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    obj = db.get(Faq, faq_id)
    if not obj:
        raise HTTPException(status_code=404, detail="FAQ not found")
    db.delete(obj)
    db.commit()


# ── Reader Questions ───────────────────────────────────────────────────────────

@router.post("/assets/{asset_id}/questions", response_model=ReaderQuestionOut, status_code=status.HTTP_201_CREATED)
def submit_question(asset_id: uuid.UUID, body: ReaderQuestionCreate, db: DbDep):
    """Public — no auth required."""
    if not db.get(ContentAsset, asset_id):
        raise HTTPException(status_code=404, detail="Content asset not found")
    obj = ReaderQuestion(content_asset_id=asset_id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/assets/{asset_id}/questions", response_model=list[ReaderQuestionOut])
def list_questions(asset_id: uuid.UUID, _admin: AdminDep, db: DbDep):
    if not db.get(ContentAsset, asset_id):
        raise HTTPException(status_code=404, detail="Content asset not found")
    return db.scalars(
        select(ReaderQuestion)
        .where(ReaderQuestion.content_asset_id == asset_id)
        .order_by(ReaderQuestion.created_at.desc())
    ).all()


@router.patch("/questions/{question_id}", response_model=ReaderQuestionOut)
def update_question_status(
    question_id: uuid.UUID,
    status: Annotated[str, Query()],
    _admin: AdminDep,
    db: DbDep,
):
    obj = db.get(ReaderQuestion, question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    if status not in ("pending", "answered", "dismissed"):
        raise HTTPException(status_code=400, detail="status must be pending, answered, or dismissed")
    obj.status = status
    db.commit()
    db.refresh(obj)
    return obj
