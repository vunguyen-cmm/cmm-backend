"""Storage API router — general-purpose image upload to S3."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, UploadFile

from src.auth.deps import AdminDep
from src.config import settings
from src.storage.s3_client import S3ClientDep

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}


@router.post("/upload-image")
async def upload_image(file: UploadFile, _admin: AdminDep, s3: S3ClientDep):
    """Upload an image to S3 and return its public URL."""
    if not file.content_type or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}",
        )

    ext = ALLOWED_CONTENT_TYPES[file.content_type]
    file_id = uuid.uuid4()
    s3_key = f"uploads/{file_id}.{ext}"

    data = await file.read()
    s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=s3_key,
        Body=data,
        ContentType=file.content_type,
    )

    url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
    return {"url": url}
