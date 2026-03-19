# College Money Method — PostgreSQL Database Design

## On Generated Columns

PostgreSQL's `GENERATED ALWAYS AS (...) STORED` works **only for expressions over columns within the same row** — which is exactly what your Drizzle `averageRating` example does (summing `review_*_rating_count` columns all sitting in the same row).

**`Count (Workshop Attendees)` and `Count (Workshop Registrations)` are different.** They aggregate rows from a *separate table* (`workshop_registrations`). PostgreSQL cannot cross table boundaries in a generated column.

For those, three clean solutions exist in a FastAPI stack:

| Approach | When to use |
|---|---|
| **SQLAlchemy `column_property`** (correlated subquery) | Real-time counts, small-to-medium scale |
| **Database VIEW / Materialized VIEW** | Read-heavy queries, reporting, APIs that don't own the model |
| **Explicit cached column + trigger** | Very high-read, low-write scenarios |

Examples for all three are shown at the bottom of this file.

---

## Schema DDL

```sql
-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE sales_status_enum AS ENUM (
    'Prospect',
    'Proposal Sent',
    'Proposal Accepted',
    'Proposal Rejected',
    'Contract Signed',
    'Not Moving Forward',
    'Current Customer'
);

CREATE TYPE proposal_type_enum AS ENUM ('Fixed', 'Variable');

CREATE TYPE registration_status_enum AS ENUM ('approved', 'pending', 'denied');

CREATE TYPE cycle_status_enum AS ENUM ('Current', 'Next', 'Archive');


-- ============================================================
-- CYCLES
-- Academic year containers. Everything is scoped to a cycle.
-- ============================================================

CREATE TABLE cycles (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT        NOT NULL UNIQUE,   -- e.g. '2024-2025'
    beginning_date  DATE        NOT NULL,
    end_date        DATE        NOT NULL,
    is_current      BOOLEAN     NOT NULL DEFAULT FALSE,
    next_cycle_id   UUID        REFERENCES cycles(id),
    prev_cycle_id   UUID        REFERENCES cycles(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT one_current_cycle EXCLUDE USING btree (is_current WITH =)
        WHERE (is_current = TRUE)  -- only one cycle can be current at a time
);


-- ============================================================
-- COHORTS
-- Regional groups of schools that share live webinar sessions.
-- ============================================================

CREATE TABLE cohorts (
    id                          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    name                        TEXT    NOT NULL UNIQUE,  -- 'BOS', 'TX', 'EAST'
    hide_unavailability_calendar BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- SCHOOLS
-- Core client entities.
-- ============================================================

CREATE TABLE schools (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    TEXT        NOT NULL,
    street_address          TEXT,
    city                    TEXT,
    state                   CHAR(2),
    zip_code                TEXT,
    enrollment_9_12         INTEGER,

    -- ✅ VALID generated column: computed from a column in this same row
    enrollment_range        TEXT        GENERATED ALWAYS AS (
        CASE
            WHEN enrollment_9_12 IS NULL  THEN NULL
            WHEN enrollment_9_12 < 250    THEN '< 250'
            WHEN enrollment_9_12 <= 500   THEN '250 - 500'
            ELSE '> 500'
        END
    ) STORED,

    cmm_website_password    TEXT,
    slug                    TEXT        UNIQUE,
    school_resource_center_url TEXT,
    appointlet_link         TEXT,
    calendar_link           TEXT,
    logo_url                TEXT,
    is_current_customer     BOOLEAN     NOT NULL DEFAULT FALSE,
    cohort_id               UUID        REFERENCES cohorts(id),
    bubble_rec_id           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- CONTACTS
-- Counselors/staff at a school.
-- ============================================================

CREATE TABLE contacts (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID        NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    first_name      TEXT,
    last_name       TEXT,

    -- ✅ VALID generated column: same-row string concat
    full_name       TEXT        GENERATED ALWAYS AS (
        TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
    ) STORED,

    email           TEXT,
    role            TEXT,
    magic_link      TEXT,
    receive_comms   BOOLEAN     NOT NULL DEFAULT TRUE,
    auto_emails     BOOLEAN     NOT NULL DEFAULT FALSE,
    softr_access    BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- WORKSHOPS
-- Template/type definitions for each workshop topic.
-- Not scheduled instances — pure content metadata.
-- ============================================================

CREATE TABLE workshops (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT    NOT NULL,
    description         TEXT,
    key_actions         TEXT,           -- markdown bullet points
    sequence_number     INTEGER UNIQUE, -- ordering within the series
    suggested_grades    TEXT,           -- e.g. '9th-12th'
    resource_center_slug TEXT   UNIQUE,
    workshop_art_url    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- WEBINARS  (formerly: Junction Table School Workshop)
-- Scheduled instances of a workshop topic.
-- One row = one live Zoom session for a cohort in a cycle.
-- ============================================================

CREATE TABLE webinars (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_id     UUID        NOT NULL REFERENCES workshops(id),
    cohort_id       UUID        NOT NULL REFERENCES cohorts(id),
    cycle_id        UUID        NOT NULL REFERENCES cycles(id),
    webinar_name    TEXT,               -- display name for counselor portal
    zoom_webinar_id TEXT        UNIQUE,
    start_datetime  TIMESTAMPTZ,
    end_datetime    TIMESTAMPTZ,

    -- ✅ VALID generated column: arithmetic on two columns in this same row
    duration_minutes INTEGER    GENERATED ALWAYS AS (
        CASE
            WHEN start_datetime IS NOT NULL AND end_datetime IS NOT NULL
            THEN EXTRACT(EPOCH FROM (end_datetime - start_datetime))::INTEGER / 60
            ELSE NULL
        END
    ) STORED,

    join_url            TEXT,
    start_url           TEXT,
    registration_url    TEXT,
    zoom_link           TEXT,
    video_embed_code    TEXT,
    audio_transcript    TEXT,
    track_registrations BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (workshop_id, cohort_id, cycle_id)
);

-- NOTE: Schools participate in a webinar via their cohort_id.
-- schools.cohort_id = webinars.cohort_id is the implicit join.
-- No extra junction table needed unless you need per-school overrides.


-- ============================================================
-- WORKSHOP REGISTRATIONS
-- One row per family member who registers for a specific webinar.
-- ============================================================

CREATE TABLE workshop_registrations (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    webinar_id          UUID        NOT NULL REFERENCES webinars(id) ON DELETE CASCADE,
    school_id           UUID        REFERENCES schools(id),
    first_name          TEXT,
    last_name           TEXT,

    -- ✅ VALID generated column: same-row concat
    full_name           TEXT        GENERATED ALWAYS AS (
        TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
    ) STORED,

    email               TEXT        NOT NULL,
    grade               TEXT,
    status              registration_status_enum NOT NULL DEFAULT 'approved',
    attended            BOOLEAN     NOT NULL DEFAULT FALSE,
    join_time           TIMESTAMPTZ,
    leave_time          TIMESTAMPTZ,
    zoom_registrant_id  TEXT,
    questions           TEXT,
    registration_time   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- PORTAL MAPPING
-- Joins one school to one webinar for the counselor portal.
-- Drives per-school portal display: ratios, videos, navigation.
-- ============================================================

CREATE TABLE portal_mapping (
    id                              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id                       UUID        NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    webinar_id                      UUID        NOT NULL REFERENCES webinars(id) ON DELETE CASCADE,
    pre_webinar_reminder_sent_on    TIMESTAMPTZ,
    post_webinar_update_sent_on     TIMESTAMPTZ,
    show_zoom                       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, webinar_id)
);


-- ============================================================
-- SALES
-- One record per school per cycle contract.
-- ============================================================

CREATE TABLE sales (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id               UUID        NOT NULL REFERENCES schools(id),
    cycle_id                UUID        NOT NULL REFERENCES cycles(id),
    contract_signatory_id   UUID        REFERENCES contacts(id),
    status                  sales_status_enum NOT NULL DEFAULT 'Prospect',
    proposal_type           proposal_type_enum,
    contract_url            TEXT,
    contract_doc_id         TEXT,
    proposal_url            TEXT,
    proposal_doc_id         TEXT,
    contract_signed_date    DATE,
    contract_sent_date      DATE,
    contract_created_at     TIMESTAMPTZ,
    proposal_sent_date      DATE,
    proposal_accepted       BOOLEAN     NOT NULL DEFAULT FALSE,
    proposal_rejected       BOOLEAN     NOT NULL DEFAULT FALSE,
    fixed_cost              NUMERIC(10, 2),
    signed_revenue          NUMERIC(10, 2),
    revenue_potential       NUMERIC(10, 2),
    contract_rate           NUMERIC(10, 2),
    hours_contracted_1on1   NUMERIC(5, 1),
    payments_received       BOOLEAN     NOT NULL DEFAULT FALSE,
    enrollment_at_signing   INTEGER,    -- snapshot of enrollment when signed
    wp_updated              BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- INVOICES
-- Billing records tied to a sales contract.
-- ============================================================

CREATE TABLE invoices (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_id    UUID        NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    amount      NUMERIC(10, 2),
    issued_date DATE,
    due_date    DATE,
    paid_date   DATE,
    status      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- ASSETS
-- Email templates, announcements, and resources.
-- ============================================================

CREATE TABLE assets (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT        NOT NULL,
    description     TEXT,
    file_link       TEXT,
    attachment_url  TEXT,
    asset_date      DATE,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    cycle_id        UUID        REFERENCES cycles(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Many-to-many: an asset can belong to multiple workshop types
CREATE TABLE workshop_assets (
    workshop_id UUID NOT NULL REFERENCES workshops(id) ON DELETE CASCADE,
    asset_id    UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    PRIMARY KEY (workshop_id, asset_id)
);


-- ============================================================
-- ONE-ON-ONE MEETINGS
-- Advisory sessions between CMM and individual families.
-- ============================================================

CREATE TABLE one_on_one_meetings (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id               UUID        REFERENCES schools(id),
    cycle_id                UUID        REFERENCES cycles(id),
    first_name              TEXT,
    last_name               TEXT,

    -- ✅ VALID generated column
    full_name               TEXT        GENERATED ALWAYS AS (
        TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
    ) STORED,

    email                   TEXT,
    grade                   TEXT,
    scheduled_at            TIMESTAMPTZ,
    status                  TEXT,
    meeting_goals           TEXT,
    notes                   TEXT,
    college_list            TEXT,
    conference_url          TEXT,
    is_school_sponsored     BOOLEAN     NOT NULL DEFAULT FALSE,
    is_invoiced             BOOLEAN     NOT NULL DEFAULT FALSE,
    ai_meeting_summary      TEXT,
    reminder_1_sent_on      TIMESTAMPTZ,
    reminder_2_sent_on      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- SCHOOL DATE SELECTOR
-- Utility table for assigning workshop dates to schools
-- during the scheduling workflow.
-- ============================================================

CREATE TABLE school_date_selector (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id   UUID    NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    workshop_id UUID    REFERENCES workshops(id),
    date        DATE    NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- PAUL MARTIN CALENDAR
-- Synced Google Calendar events for availability/scheduling.
-- ============================================================

CREATE TABLE paul_martin_calendar (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT,
    start_datetime   TIMESTAMPTZ,
    end_datetime     TIMESTAMPTZ,
    google_event_id  TEXT        UNIQUE,
    event_link       TEXT,
    hangouts_link    TEXT,
    description      TEXT,
    location         TEXT,
    status           TEXT,
    creator          TEXT,
    is_recurring     BOOLEAN     NOT NULL DEFAULT FALSE,
    is_all_day       BOOLEAN     NOT NULL DEFAULT FALSE,
    google_updated_at TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- SETTINGS
-- Automation configuration (Make.com webhooks etc.)
-- ============================================================

CREATE TABLE settings (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT    NOT NULL,
    action      TEXT,
    days_prior  INTEGER,
    trigger_url TEXT,
    webhook_url TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- INDEXES
-- ============================================================

-- High-frequency lookups
CREATE INDEX idx_contacts_school_id         ON contacts(school_id);
CREATE INDEX idx_webinars_workshop_id        ON webinars(workshop_id);
CREATE INDEX idx_webinars_cohort_id          ON webinars(cohort_id);
CREATE INDEX idx_webinars_cycle_id           ON webinars(cycle_id);
CREATE INDEX idx_webinars_start_datetime     ON webinars(start_datetime);
CREATE INDEX idx_workshop_reg_webinar_id     ON workshop_registrations(webinar_id);
CREATE INDEX idx_workshop_reg_school_id      ON workshop_registrations(school_id);
CREATE INDEX idx_workshop_reg_email          ON workshop_registrations(email);
CREATE INDEX idx_portal_mapping_school_id    ON portal_mapping(school_id);
CREATE INDEX idx_portal_mapping_webinar_id   ON portal_mapping(webinar_id);
CREATE INDEX idx_sales_school_id             ON sales(school_id);
CREATE INDEX idx_sales_cycle_id              ON sales(cycle_id);
CREATE INDEX idx_sales_status                ON sales(status);
CREATE INDEX idx_schools_cohort_id           ON schools(cohort_id);
CREATE INDEX idx_schools_slug                ON schools(slug);
CREATE INDEX idx_1on1_school_id              ON one_on_one_meetings(school_id);
CREATE INDEX idx_1on1_cycle_id               ON one_on_one_meetings(cycle_id);
```

---

## Cross-Table Counts: The Three Patterns

### ❌ What doesn't work
```sql
-- INVALID — PostgreSQL generated columns cannot reference other tables
ALTER TABLE webinars ADD COLUMN registration_count INTEGER
    GENERATED ALWAYS AS (
        SELECT COUNT(*) FROM workshop_registrations WHERE webinar_id = id
    ) STORED;
-- ERROR: cannot use subquery in column generation expression
```

---

### ✅ Pattern 1 — SQLAlchemy `column_property` (recommended for FastAPI)

Computed at query time via a correlated subquery. Fully transparent in the ORM — you access `webinar.registration_count` like any other column.

```python
# models.py
from sqlalchemy import Column, Integer, Boolean, func, select
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WorkshopRegistration(Base):
    __tablename__ = "workshop_registrations"
    id         = Column(UUID, primary_key=True)
    webinar_id = Column(UUID, ForeignKey("webinars.id"), nullable=False)
    attended   = Column(Boolean, nullable=False, default=False)
    # ... other columns


class Webinar(Base):
    __tablename__ = "webinars"
    id          = Column(UUID, primary_key=True)
    workshop_id = Column(UUID, ForeignKey("workshops.id"), nullable=False)
    cohort_id   = Column(UUID, ForeignKey("cohorts.id"), nullable=False)
    cycle_id    = Column(UUID, ForeignKey("cycles.id"), nullable=False)
    # ... other columns

    registrations = relationship("WorkshopRegistration", back_populates="webinar")

# Correlated subqueries — equivalent to Airtable's Count rollup fields
Webinar.registration_count = column_property(
    select(func.count(WorkshopRegistration.id))
    .where(WorkshopRegistration.webinar_id == Webinar.id)
    .correlate_except(WorkshopRegistration)
    .scalar_subquery()
)

Webinar.attendee_count = column_property(
    select(func.count(WorkshopRegistration.id))
    .where(
        WorkshopRegistration.webinar_id == Webinar.id,
        WorkshopRegistration.attended == True,
    )
    .correlate_except(WorkshopRegistration)
    .scalar_subquery()
)
```

Usage in a FastAPI route:
```python
# routers/webinars.py
@router.get("/{webinar_id}")
async def get_webinar(webinar_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Webinar).where(Webinar.id == webinar_id)
    )
    webinar = result.scalar_one_or_none()
    # webinar.registration_count and webinar.attendee_count are available automatically
    return webinar
```

---

### ✅ Pattern 2 — Database VIEW (best for read-only APIs / reporting)

```sql
CREATE VIEW webinar_stats AS
SELECT
    w.id                                                    AS webinar_id,
    w.webinar_name,
    w.start_datetime,
    w.cycle_id,
    w.cohort_id,
    w.workshop_id,
    COUNT(r.id)                                             AS registration_count,
    COUNT(r.id) FILTER (WHERE r.attended = TRUE)            AS attendee_count,
    ROUND(
        COUNT(r.id) FILTER (WHERE r.attended = TRUE)::NUMERIC
        / NULLIF(COUNT(r.id), 0) * 100, 1
    )                                                       AS attendance_rate_pct
FROM webinars w
LEFT JOIN workshop_registrations r ON r.webinar_id = w.id
GROUP BY w.id;
```

For `portal_mapping`, the per-school ratios (registration ratio vs. school enrollment):
```sql
CREATE VIEW portal_mapping_stats AS
SELECT
    pm.id                                                   AS portal_mapping_id,
    pm.school_id,
    pm.webinar_id,
    s.enrollment_9_12,
    COUNT(r.id)                                             AS registration_count,
    COUNT(r.id) FILTER (WHERE r.attended = TRUE)            AS attendee_count,
    ROUND(
        COUNT(r.id)::NUMERIC / NULLIF(s.enrollment_9_12, 0), 4
    )                                                       AS registration_ratio,
    ROUND(
        COUNT(r.id) FILTER (WHERE r.attended = TRUE)::NUMERIC
        / NULLIF(COUNT(r.id), 0), 4
    )                                                       AS attendance_ratio
FROM portal_mapping pm
JOIN schools s ON s.id = pm.school_id
LEFT JOIN workshop_registrations r
    ON r.webinar_id = pm.webinar_id
    AND r.school_id = pm.school_id
GROUP BY pm.id, s.enrollment_9_12;
```

---

### ✅ Pattern 3 — Cached column + trigger (for very high-read workloads)

Store the count as a real column, keep it updated with a trigger. Trade-off: write overhead, but zero join cost on reads.

```sql
-- Add cached columns to webinars
ALTER TABLE webinars
    ADD COLUMN registration_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN attendee_count     INTEGER NOT NULL DEFAULT 0;

-- Trigger function
CREATE OR REPLACE FUNCTION update_webinar_counts()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE webinars SET
        registration_count = (
            SELECT COUNT(*) FROM workshop_registrations WHERE webinar_id = NEW.webinar_id
        ),
        attendee_count = (
            SELECT COUNT(*) FROM workshop_registrations
            WHERE webinar_id = NEW.webinar_id AND attended = TRUE
        )
    WHERE id = NEW.webinar_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fire after every insert/update/delete on workshop_registrations
CREATE TRIGGER trg_webinar_counts
AFTER INSERT OR UPDATE OR DELETE ON workshop_registrations
FOR EACH ROW EXECUTE FUNCTION update_webinar_counts();
```

---

## Summary of Generated vs Computed Approaches

| Column | Table | Approach | Reason |
|---|---|---|---|
| `enrollment_range` | `schools` | `GENERATED ALWAYS AS` ✅ | Same-row CASE on `enrollment_9_12` |
| `duration_minutes` | `webinars` | `GENERATED ALWAYS AS` ✅ | Same-row arithmetic on `start_datetime` / `end_datetime` |
| `full_name` | `contacts`, `workshop_registrations`, `one_on_one_meetings` | `GENERATED ALWAYS AS` ✅ | Same-row string concat |
| `registration_count` | `webinars` | `column_property` or VIEW | Aggregates rows from `workshop_registrations` |
| `attendee_count` | `webinars` | `column_property` or VIEW | Aggregates rows from `workshop_registrations` |
| `registration_ratio` | `portal_mapping` | VIEW | Divides count from `workshop_registrations` by `schools.enrollment_9_12` |
| `attendance_ratio` | `portal_mapping` | VIEW | Attended ÷ registered, cross-table |

---

## Entity Relationship Overview

```
cycles
  │
  ├──< webinars >── workshops
  │        │             └──< workshop_assets >── assets
  │        ├── cohorts
  │        │      └──< schools >── contacts
  │        │                  └──< sales >── invoices
  │        │                  └──< one_on_one_meetings
  │        │                  └──< school_date_selector
  │        │
  │        ├──< workshop_registrations (school_id FK)
  │        │
  │        └──< portal_mapping (school_id FK)
  │
  └──< sales
  └──< one_on_one_meetings

paul_martin_calendar   (standalone, no FK relations)
settings               (standalone, no FK relations)
```
