#!/usr/bin/env python3
"""Upload one or more image URLs to S3 and print the permanent S3 URLs.

Usage:
    python scripts/upload_to_s3.py <url> [<url> ...]
    python scripts/upload_to_s3.py https://www.figma.com/api/mcp/asset/abc123

Each URL is downloaded, uploaded to the configured S3 bucket under the
`portal/assets/` prefix, and the resulting S3 URL is printed to stdout.

Configuration is read from the .env file in the backend root (same as the app).

Dependencies: boto3, requests, python-dotenv (all already in the project).
"""

from __future__ import annotations

import hashlib
import mimetypes
import sys
import urllib.parse
from pathlib import Path

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError

# Load settings from .env via the project's config
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import settings  # noqa: E402


S3_PREFIX = "portal/assets"


def _ext_from_content_type(content_type: str) -> str:
    """Best-guess file extension from a Content-Type header value."""
    # Strip parameters like '; charset=utf-8'
    mime = content_type.split(";")[0].strip()
    ext = mimetypes.guess_extension(mime)
    # Python maps image/jpeg -> .jpeg; normalise common ones
    return {".jpeg": ".jpg", ".jpe": ".jpg", None: ".bin"}.get(ext, ext or ".bin")


def upload_url(url: str, s3_client, bucket: str) -> str:
    """Download *url* and upload it to S3. Returns the public S3 HTTPS URL."""
    print(f"  Downloading {url[:80]}...", file=sys.stderr)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    ext = _ext_from_content_type(content_type)

    # Use a hash of the original URL as the S3 key so re-uploading the same
    # asset is idempotent.
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    s3_key = f"{S3_PREFIX}/{url_hash}{ext}"

    print(f"  Uploading to s3://{bucket}/{s3_key} ({content_type})", file=sys.stderr)
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=resp.content,
        ContentType=content_type.split(";")[0].strip(),
    )

    region = settings.aws_region
    s3_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
    return s3_url


def main() -> None:
    urls = sys.argv[1:]
    if not urls:
        print("Usage: python scripts/upload_to_s3.py <url> [<url> ...]", file=sys.stderr)
        sys.exit(1)

    if not settings.s3_bucket_name:
        print("Error: s3_bucket_name is not set in .env", file=sys.stderr)
        sys.exit(1)

    s3 = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    for url in urls:
        try:
            s3_url = upload_url(url, s3, settings.s3_bucket_name)
            print(s3_url)
        except (requests.RequestException, BotoCoreError, ClientError) as exc:
            print(f"Error uploading {url}: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
