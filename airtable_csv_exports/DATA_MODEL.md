# College Money Method — Airtable Data Model

This document describes each table in the Airtable export and the relationships between them.

---

## Tables

### 1. Schools
**File:** `Schools.csv`

The central entity in the data model. Each row represents a private school that is either a current client, a prospect, or a past client of College Money Method (CMM).

**Key fields:**
- `School` — Full name of the school
- `City`, `State`, `Street Address`, `Zip Code` — Physical location
- `Enrollment (9-12)` / `Enrollment Range` — Size indicator used for pricing
- `CMM Website Password` — Portal access credential for the school's counselor
- `slug` — URL-friendly identifier used in the CMM resource center
- `School Resource Center URL` — The school-specific family portal URL
- `Current Customer` — Boolean flag indicating active client status
- `Magic Link (from Contacts)` — Counselor's magic-link login for the portal
- `Cohort 2` — Link to the school's regional **Cohort**
- `Contacts` — Linked counselor/staff records
- `Sales` — Linked sales/contract records
- `Junction Table School Workshop` *(renamed: Webinars)* — All webinar instances for this school
- `Workshop Registrations` — All family registrations from this school
- `Portal Mapping Table` — Portal-specific mapping records
- `One-on-one Meetings` — 1:1 advisory meetings for families from this school
- `School Date Selector` — Available/assigned workshop dates

---

### 2. Contacts
**File:** `Contacts.csv`

Individual people at a school — typically the college counselor or director responsible for the CMM partnership. Each contact belongs to one school.

**Key fields:**
- `First Name`, `Last Name`, `Email` — Personal info
- `Role` — Their role at the school
- `Sch` / `School (from Sch)` — Link back to the parent **School**
- `Magic Link` — Passwordless login URL for the counselor portal
- `Receive Comms` — Whether this contact receives automated emails
- `Auto Emails` — Boolean flag for email automation
- `Current Customer` — Rolled up from the linked school
- `Sales` — Linked sales records (used for contract signatory tracking)
- `Softr Access` — Whether they have access to the Softr-based portal

---

### 3. Workshops
**File:** `Workshops.csv`

Workshop *templates* — the canonical definitions of each workshop topic that CMM delivers. These are not scheduled instances; they define content, sequencing, and metadata.

**Key fields:**
- `Name` — Workshop title (e.g., "Understanding How Colleges Assess Your Ability to Pay and Aid Eligibility")
- `Description` — Full description of the workshop's content and purpose
- `Workshop Key Actions` — Bullet-point takeaways for families
- `Webinar Sequence` — Numeric ordering of the workshop in the series
- `Suggested Grades` — Target audience (e.g., 9th–12th grade)
- `Resource Center Slug` — Path used in the family resource center URL
- `Workshop Art` — Thumbnail/image asset attachment
- `WorkshopTypeRecID` — Self-referential ID (used in lookups from other tables)
- `Junction Table School Workshop 2` *(renamed: Webinars)* — All scheduled instances of this workshop
- `Comms` — Related communication assets

---

### 4. Webinars
**File:** `Webinars.csv`
*(Originally named: Junction Table School Workshop)*

The scheduled instances of a workshop. Each row represents one live Zoom webinar — a specific workshop topic delivered to a specific cohort of schools during a specific academic cycle. This is the operational heart of CMM's delivery model.

**Key fields:**
- `Name (from Workshops)` — The workshop topic being delivered
- `Webinar Name` — Display name combining topic + schools
- `Start Date and Time`, `End Date and Time`, `Duration` — Scheduling info
- `JoinURL`, `StartURL`, `Zoom Link` — Zoom meeting links
- `RegistrationURL` — Link families use to register
- `Webinar ID` — Zoom's internal webinar ID
- `Cohort` — The regional **Cohort** this webinar is for
- `Schools` — The specific schools participating
- `Cycle` — The academic year **Cycle** this falls in
- `Workshops` — The **Workshop** template this is an instance of
- `Workshop Registrations` — All individual family registrations for this session
- `Portal Mapping Table` — Per-school portal mapping records
- `Count (Workshop Attendees)` / `Count (Workshop Registrations)` — Rollup attendance stats
- `Current (from Cycle)`, `Cycle (Current/Next/Archive)` — Status of the academic year
- `Track Registrations` — Whether to sync registration data
- `Video Embed Code` — Embed code for the post-webinar recording
- `Audio Transcript` — Transcript of the webinar recording

---

### 5. Workshop Registrations
**File:** `Workshop Registrations.csv`

Individual registration records — one row per family member (student or parent) who registers for a specific webinar. This is the most granular record of participation.

**Key fields:**
- `First Name`, `Last Name`, `Email` — Registrant info
- `Grade` — Student's current grade
- `School` / `SchoolName` — The school the family is associated with
- `Junction Table School Workshop` *(renamed: Webinar)* — The specific webinar they registered for
- `Workshops (from Junction Table School Workshop)` — The workshop topic
- `Status` — Registration status (e.g., `approved`)
- `Attended` — Whether the registrant actually attended
- `Join Time`, `Leave Time` — Attendance timestamps from Zoom
- `ZoomRegistrantID` — Zoom's unique registrant identifier
- `Questions` — Any questions submitted by the registrant
- `Portal Mapping Table` — Linked portal mapping record
- `Webinar ID` — Zoom webinar ID (for cross-referencing)

---

### 6. Cohort
**File:** `Cohort.csv`

A regional grouping of schools that share webinar sessions together. CMM runs workshops cohort-by-cohort rather than school-by-school, allowing multiple schools in the same region to attend the same live session.

**Key fields:**
- `Name` — Short identifier for the cohort (e.g., `BOS`, `TX`, `BAISCC`, `EAST`)
- `School (from School)` — The schools in this cohort (displayed names)
- `School` — Linked **Schools** records
- `Junction Table School Workshop` *(renamed: Webinars)* — All webinar instances for this cohort
- `Hide Unavailability Calendar` — UI flag for the scheduling calendar
- `CohortRecID` — Self-referential ID

---

### 7. Cycle
**File:** `Cycle.csv`

An academic year cycle (e.g., `2024-2025`, `2025-2026`). All webinars, sales, and operations are scoped to a cycle. The `Current` flag marks the active year.

**Key fields:**
- `Name` — Academic year label (e.g., `2024-2025`)
- `Beginning Date`, `End Date` — Start and end of the cycle
- `Current` — Boolean indicating the active cycle
- `Next` — Points to the following cycle
- `Previous` — Points to the preceding cycle
- `Cycle to copy from` — Used to clone webinar schedules from a prior year
- `Initiate Copy` — Trigger field for the copy automation
- `Junction Table School Workshop` *(renamed: Webinars)* — All webinars in this cycle
- `Sales` — All sales/contracts active in this cycle
- `One-on-one Meetings` — All 1:1 meetings in this cycle
- `Comms` — Communication records for the cycle

---

### 8. Sales
**File:** `Sales.csv`

Tracks the business/sales relationship with each school per cycle. One record typically corresponds to one school-year contract.

**Key fields:**
- `Schools` / `School (from Schools)` — The contracted school
- `Cycle` — The academic cycle this contract covers
- `Sales Status` — Pipeline stage (e.g., `Proposal Sent`, `Contract Signed`, `Not Moving Forward`)
- `Contract` — Attached signed contract PDF
- `Contract Signed`, `Contract Sent`, `Contract Signatory` — Contract tracking
- `Proposal` / `Proposal Type` — Attached proposal and type (`Fixed` vs. variable)
- `Fixed Cost`, `Signed Revenue`, `Revenue Potential` — Financial figures
- `Contract Rate` — Per-student rate
- `1-1 hours contracted` — Number of 1:1 advisory hours in the contract
- `Invoices Raised` — Count of invoices generated
- `Payments Received` — Whether payment has been received
- `Enrollment (9-12) (from Schools)` — School size at time of sale

---

### 9. Invoices
**File:** `Invoices.csv`

Intended to track billing records. Currently empty — only `id` and `createdTime` columns are present.

---

### 10. Assets
**File:** `Assets.csv`

Content assets associated with specific workshops or cycles — primarily email templates, announcements, and follow-up communications that go out to families.

**Key fields:**
- `Name` — Asset title (e.g., "Workshop 1 Announcement", "Senior Communication: October 2024")
- `Asset Description` — Brief description of the content
- `File Link` — Google Docs link to the actual document
- `Attachment` — Direct file attachment (if any)
- `Date` — Date the asset is relevant to or was created
- `Active` — Whether the asset is currently in use
- `Cycle` — The academic cycle this asset belongs to
- `Workshops` — The specific workshop(s) this asset is associated with
- `WorkshopTypeRecID (from Workshops)` — Lookup to the workshop type

---

### 11. Settings
**File:** `Settings.csv`

System configuration table for automation triggers. Contains a single row that defines a Make.com webhook used to bulk-update webinar records.

**Key fields:**
- `Name` — Description of the setting
- `Action` — The action to trigger (e.g., `UpdateAllWebinars`)
- `Days Prior` — How many days prior to today the action applies
- `Trigger` — Button URL that fires the webhook
- `Webhook` — The Make.com webhook endpoint

---

### 12. Portal Mapping Table
**File:** `Portal Mapping Table.csv`

Maps a specific school to a specific webinar for the counselor-facing portal. This allows the portal to display the correct webinar details, registration links, videos, and attendance stats for each school's view.

**Key fields:**
- `Schools` — The linked **School**
- `Webinar` — The linked **Webinar** instance
- `Workshops (from Webinar)` — The workshop topic
- `Name` — Display name combining workshop + school context
- `Start Date and Time (from Webinar)` — When the webinar is scheduled
- `Registration Ratio`, `Attendance Ratio` — Calculated engagement metrics
- `Video Embed Code` / `Video Embed Code (from Webinar)` — Post-webinar recording embed
- `SchoolWebinarMapRecID` — Unique identifier for this mapping record
- `Upcoming Workshop` / `Previous Webinar` — Navigation links between sessions
- `Pre-Webinar Reminder Sent on`, `Post-Webinar Update Sent on` — Communication tracking
- `Counselor Hub Workshop Details Page` — URL for the counselor to view this session's details
- `Workshop Registrations` — All registrations for this school+webinar combination
- `Track Registrations (from Webinar)` — Whether registration sync is active

---

### 13. One-on-one Meetings
**File:** `One-on-one Meetings.csv`

Records of individual 1:1 advisory meetings between CMM (Paul Martin) and a family from a client school. These are part of the contracted service offering.

**Key fields:**
- `First Name`, `Last Name`, `Email` — Family member info
- `Grade` — Student's grade level
- `School` — Linked **School** (the client institution)
- `School Name` — Displayed school name
- `Cycle` — The academic cycle the meeting falls in
- `Date` — Scheduled meeting date/time
- `Status` — Appointment status
- `Meeting Goals` — What the family wants to accomplish
- `Notes` — Advisor's session notes
- `College List` — Colleges under consideration
- `Conference URL` — Zoom/video link
- `School Sponsored` — Whether the meeting is covered under the school's contract
- `Invoiced` — Whether the session has been billed
- `Reminder 1 Sent On`, `Reminder 2 Sent On` — Automated reminder tracking
- `Logo (from School)` — School logo for display
- `AI Meeting Summaries` — AI-generated summary of the meeting notes

---

### 14. School Date Selector
**File:** `School Date Selector.csv`

A utility table that tracks specific dates associated with schools — used in the scheduling workflow to assign available webinar dates to individual schools within a cohort.

**Key fields:**
- `Schools` — The **School** this date is for
- `Cohort 2 (from Schools)` — The cohort the school belongs to
- `Date` — The specific date being assigned or considered
- `DateAsString` — String representation of the date (used in formulas)
- `Workshops` — Any workshops linked to this date slot
- `Calculation` — Formula field used in scheduling logic

---

### 15. PAUL MARTIN
**File:** `PAUL MARTIN.csv`

A sync of Paul Martin's Google Calendar events. Used to surface his availability and schedule in Airtable automations and views.

**Key fields:**
- `Title` — Calendar event title
- `Start`, `End` — Event start and end times
- `Event ID` — Google Calendar's unique event ID
- `Status` — Event status (e.g., `confirmed`)
- `Creator` — Always `paul.martin@collegemoneymethod.com`
- `Attendees` — Other attendees (if any)
- `Description` — Event description
- `Event Link` — Link to view in Google Calendar
- `Recurring Event` — Whether this is a recurring event
- `All Day` — Whether it's an all-day event

---

## Relationships

```
Cycle ──────────────────────────────────────────────┐
  │ (one cycle per academic year)                    │
  │                                                  │
  ├──< Webinars (Junction Table School Workshop)     │
  │        │ (many webinar instances per cycle)      │
  │        │                                         │
  │        ├── Workshop (template/type) ─────────────┤
  │        │      └──< Assets                        │
  │        │                                         │
  │        ├── Cohort ──────────────────────────────>│
  │        │      └──< Schools                       │
  │        │                                         │
  │        ├──< Workshop Registrations               │
  │        │        └── School (via lookup)          │
  │        │                                         │
  │        └──< Portal Mapping Table                 │
  │                  └── School (one per school)     │
  │                                                  │
  └──< Sales ──────────────────────────────────────>─┘
           └── School

Schools ──< Contacts
Schools ──< One-on-one Meetings
Schools ──< School Date Selector
```

### Detailed relationship descriptions

| Relationship | Type | Notes |
|---|---|---|
| **Cycle → Webinars** | One-to-many | Each cycle contains many scheduled webinar sessions |
| **Workshop → Webinars** | One-to-many | A workshop template is instantiated into many sessions across cycles |
| **Cohort → Schools** | One-to-many | Each cohort groups multiple schools in the same region |
| **Cohort → Webinars** | One-to-many | All schools in a cohort share the same webinar sessions |
| **School → Contacts** | One-to-many | A school has one or more counselor contacts |
| **School → Sales** | One-to-many | A school can have sales records across multiple cycles |
| **Webinar → Workshop Registrations** | One-to-many | Families register individually for each webinar session |
| **School → Workshop Registrations** | One-to-many | A school's families each have their own registration records |
| **Webinar → Portal Mapping Table** | One-to-many | Each webinar has one portal mapping record per participating school |
| **School → Portal Mapping Table** | One-to-many | Each school has mapping records for every webinar they participate in |
| **School → One-on-one Meetings** | One-to-many | Families from a school book 1:1 advisory sessions |
| **Cycle → Sales** | One-to-many | Sales contracts are scoped to a specific academic cycle |
| **Workshop → Assets** | One-to-many | Each workshop type has associated communication assets |
| **Cycle → Assets** | One-to-many | Assets (communications) belong to a specific cycle |

### Key design patterns

- **Webinars is the central junction table.** It connects Workshops (what is being taught), Cohorts/Schools (who is being taught), and Cycles (when it is happening). Nearly every operational table links back to it.

- **Cohorts enable shared sessions.** Rather than creating a separate Zoom webinar per school, CMM groups schools regionally into cohorts and runs a single session. The Portal Mapping Table then provides each school its own personalized view of that shared session.

- **Portal Mapping Table is the per-school view layer.** It joins a School and a Webinar into a single record that drives the counselor portal display — including registration counts, attendance ratios, video embeds, and next/previous workshop navigation.

- **Cycle controls what is "current."** The `Current` flag on the Cycle table cascades through lookups in Webinars, Sales, and One-on-one Meetings to filter views to the active academic year.

- **Workshop Registrations bridge families to sessions.** They are created via Zoom registration and carry attendance data (join/leave times) back into Airtable, enabling rollup counts visible in the Webinars and Portal Mapping tables.
