"""Create counselor accounts from school contacts.

For each contact with an email, creates a Supabase Auth user with a random
password and assigns the 'counselor' role linked to the contact's school.
Outputs a CSV with email/password pairs so credentials can be shared.

Usage:
    uv run python scripts/seed_counselors_from_contacts.py
    uv run python scripts/seed_counselors_from_contacts.py --dry-run
    uv run python scripts/seed_counselors_from_contacts.py --output credentials.csv
"""

from __future__ import annotations

import argparse
import csv
import secrets
import string
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import joinedload, Session
from supabase import create_client

from src.auth.models import UserRole
from src.config import settings
from src.db.deps import get_db
from src.schools.models import Contact, School

# Import all models so SQLAlchemy can resolve relationships
import src.assets.models  # noqa: F401
import src.content.models  # noqa: F401
import src.cycles.models  # noqa: F401
import src.meetings.models  # noqa: F401
import src.sales.models  # noqa: F401
import src.settings.models  # noqa: F401
import src.workshops.models  # noqa: F401


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    # Shuffle so the guaranteed characters aren't always at the start
    pw_list = list(password)
    secrets.SystemRandom().shuffle(pw_list)
    return "".join(pw_list)


def get_existing_counselor_emails(db: Session, supabase) -> set[str]:
    """Return the set of emails that already have a counselor/viewer role."""
    role_records = (
        db.query(UserRole)
        .filter(UserRole.role.in_(["counselor", "viewer"]))
        .all()
    )
    emails = set()
    for record in role_records:
        try:
            resp = supabase.auth.admin.get_user_by_id(str(record.user_id))
            if resp and resp.user and resp.user.email:
                emails.add(resp.user.email.lower())
        except Exception:
            pass
    return emails


def main() -> None:
    parser = argparse.ArgumentParser(description="Create counselor accounts from school contacts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument(
        "--output", "-o",
        default=f"counselor_credentials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        help="Output CSV file path (default: counselor_credentials_<timestamp>.csv)",
    )
    args = parser.parse_args()

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    db_gen = get_db()
    db = next(db_gen)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Creating counselors from school contacts...\n")

    # Get all contacts with emails, joined with their school
    contacts = (
        db.query(Contact)
        .options(joinedload(Contact.school))
        .filter(Contact.email.isnot(None))
        .filter(Contact.email != "")
        .all()
    )

    print(f"Found {len(contacts)} contacts with emails.\n")

    # Get existing counselor emails to skip duplicates
    print("Checking existing counselor accounts...")
    existing_emails = get_existing_counselor_emails(db, supabase)
    print(f"Found {len(existing_emails)} existing counselor/viewer accounts.\n")

    credentials: list[dict] = []
    skipped = 0
    errors = 0

    for contact in contacts:
        email = contact.email.strip().lower()
        school_name = contact.school.name if contact.school else "Unknown"
        first_name = contact.first_name or ""
        last_name = contact.last_name or ""

        if email in existing_emails:
            print(f"  SKIP (already exists): {email} — {school_name}")
            skipped += 1
            continue

        password = generate_password()

        print(f"  Processing: {email} — {school_name}")

        if args.dry_run:
            print(f"    [dry-run] Would create counselor: {email}")
            credentials.append({
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "school_name": school_name,
                "school_id": str(contact.school_id),
            })
            existing_emails.add(email)  # Prevent duplicate processing
            continue

        # Create Supabase Auth user with password
        create_params = {
            "email": email,
            "password": password,
            "user_metadata": {
                "first_name": first_name,
                "last_name": last_name,
            },
            "email_confirm": True,
        }

        try:
            resp = supabase.auth.admin.create_user(create_params)
            if not resp or not resp.user:
                print(f"    ERROR: Failed to create auth user for {email}")
                errors += 1
                continue
            new_user = resp.user
        except Exception as exc:
            error_msg = str(exc).lower()
            if "already" in error_msg or "exists" in error_msg or "registered" in error_msg:
                # User exists in Supabase but no counselor role — find them and assign role
                print(f"    User exists in Supabase Auth, looking up: {email}")
                try:
                    users_resp = supabase.auth.admin.list_users()
                    new_user = next(
                        (u for u in (users_resp or []) if u.email and u.email.lower() == email),
                        None,
                    )
                    if not new_user:
                        print(f"    ERROR: Could not find existing user {email}")
                        errors += 1
                        continue
                    # Update password for existing user
                    supabase.auth.admin.update_user_by_id(
                        new_user.id,
                        {"password": password},
                    )
                except Exception as exc2:
                    print(f"    ERROR looking up user {email}: {exc2}")
                    errors += 1
                    continue
            else:
                print(f"    ERROR creating user {email}: {exc}")
                errors += 1
                continue

        # Check if role record already exists
        user_id = uuid.UUID(new_user.id)
        existing_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()

        if existing_role:
            existing_role.role = "counselor"
            existing_role.school_id = contact.school_id
            db.commit()
            print(f"    Updated existing role to counselor for {email}")
        else:
            role_record = UserRole(
                user_id=user_id,
                role="counselor",
                school_id=contact.school_id,
            )
            db.add(role_record)
            db.commit()
            print(f"    Created counselor role for {email}")

        credentials.append({
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "school_name": school_name,
            "school_id": str(contact.school_id),
        })
        existing_emails.add(email)  # Prevent duplicate processing

    # Write CSV
    if credentials:
        output_path = Path(args.output)
        with output_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "password", "first_name", "last_name", "school_name", "school_id"])
            writer.writeheader()
            writer.writerows(credentials)
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Credentials written to: {output_path}")

    print(f"\nSummary:")
    print(f"  Created: {len(credentials)}")
    print(f"  Skipped (already existed): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total contacts processed: {len(contacts)}")


if __name__ == "__main__":
    main()
