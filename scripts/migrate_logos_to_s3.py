"""Migrate school logo_url fields from Airtable JSON blobs to permanent S3 URLs.

Airtable attachment URLs expire ~1 hour after generation. This script:
  1. Finds all schools whose logo_url is an Airtable JSON blob
  2. Downloads the image from Airtable
  3. Uploads it to S3 under logos/<school_id>.<ext>
  4. Updates logo_url in the DB with the public S3 URL

Usage:
    uv run python scripts/migrate_logos_to_s3.py
    uv run python scripts/migrate_logos_to_s3.py --dry-run
    uv run python scripts/migrate_logos_to_s3.py --school-id <uuid>  # single school

Requires AWS credentials and s3_bucket_name in .env.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.db.deps import get_db
from src.schools.models import School
from src.storage.s3_client import s3_client


def _parse_logo_url(raw: str) -> tuple[str, str] | None:
    """Return (download_url, file_extension) if raw is an Airtable JSON blob, else None."""
    raw = raw.strip()
    if not raw.startswith("{"):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    url = data.get("url")
    if not url:
        return None

    filename = data.get("filename", "logo")
    ext = Path(filename).suffix.lstrip(".") or "webp"
    return url, ext


def _s3_url(key: str) -> str:
    bucket = settings.s3_bucket_name
    region = settings.aws_region
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def migrate_school(school: School, s3: object, dry_run: bool) -> str | None:
    """Download logo and upload to S3. Returns new URL or None on failure."""
    result = _parse_logo_url(school.logo_url or "")
    if result is None:
        return None  # already a plain URL or empty

    download_url, ext = result
    s3_key = f"logos/{school.id}.{ext}"

    print(f"  Downloading from Airtable...")
    try:
        resp = requests.get(download_url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        print(f"  ERROR downloading: {exc}")
        return None

    content_type = resp.headers.get("content-type", f"image/{ext}")
    size_kb = len(resp.content) / 1024
    print(f"  Downloaded {size_kb:.1f} KB ({content_type})")

    if dry_run:
        new_url = _s3_url(s3_key)
        print(f"  [dry-run] Would upload to s3://{settings.s3_bucket_name}/{s3_key}")
        print(f"  [dry-run] Would set logo_url = {new_url}")
        return new_url

    print(f"  Uploading to s3://{settings.s3_bucket_name}/{s3_key}...")
    try:
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=resp.content,
            ContentType=content_type,
        )
    except Exception as exc:
        print(f"  ERROR uploading to S3: {exc}")
        return None

    new_url = _s3_url(s3_key)
    print(f"  Uploaded → {new_url}")
    return new_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate school logos to S3")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--school-id", help="Migrate a single school by UUID")
    args = parser.parse_args()

    if not settings.s3_bucket_name:
        print("ERROR: s3_bucket_name is not set in .env")
        sys.exit(1)

    s3 = s3_client()
    db = next(get_db())

    query = db.query(School)
    if args.school_id:
        query = query.filter(School.id == uuid.UUID(args.school_id))

    schools = query.all()
    needs_migration = [s for s in schools if s.logo_url and s.logo_url.strip().startswith("{")]

    print(f"{'[DRY RUN] ' if args.dry_run else ''}"
          f"Found {len(needs_migration)} school(s) with Airtable logo blobs (out of {len(schools)} total)\n")

    updated = 0
    failed = 0
    for school in needs_migration:
        print(f"School: {school.name} ({school.id})")
        new_url = migrate_school(school, s3, args.dry_run)
        if new_url:
            if not args.dry_run:
                school.logo_url = new_url
                db.commit()
            updated += 1
        else:
            failed += 1
        print()

    print(f"Done. Updated: {updated}, Failed: {failed}, Skipped (no blob): {len(schools) - len(needs_migration)}")


if __name__ == "__main__":
    main()
