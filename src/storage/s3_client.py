"""AWS S3 client and FastAPI dependency."""

from functools import lru_cache
from typing import Annotated

import boto3
from botocore.client import BaseClient
from fastapi import Depends

from src.config import settings


@lru_cache
def _create_s3_client() -> BaseClient:
    """Create boto3 S3 client (cached). Uses settings for credentials and region."""
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


def s3_client() -> BaseClient:
    """Return the shared S3 client (for use outside FastAPI)."""
    return _create_s3_client()


def get_s3_client() -> BaseClient:
    """FastAPI dependency that returns the S3 client."""
    return _create_s3_client()


# Type alias for dependency injection
S3ClientDep = Annotated[BaseClient, Depends(get_s3_client)]
