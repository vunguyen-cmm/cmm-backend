"""Storage package: S3 and other external storage."""

from src.storage.s3_client import get_s3_client, s3_client

__all__ = ["get_s3_client", "s3_client"]
