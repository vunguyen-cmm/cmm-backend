# LLM Agent Guidelines for CMM Backend

## Project Overview
This is a **FastAPI-based backend service** for the CMM system. It uses async/await patterns throughout, **Supabase (PostgreSQL)** for the primary database, and **AWS S3** for object storage (file uploads, assets).

## Technology Stack
- **Framework**: FastAPI (latest)
- **Python Version**: >=3.12
- **Database**: Supabase (PostgreSQL) via `supabase` Python client
- **ORM**: SQLAlchemy 2.0 (Mapped columns, `DeclarativeBase`)
- **Migrations**: Alembic (integrated with SQLAlchemy models)
- **Object Storage**: AWS S3 (via boto3)
- **Server**: Uvicorn with standard extras

### Optional
- **Logging**: structlog
- **Testing**: pytest, pytest-asyncio, httpx
- **Code Quality**: ruff, black, isort

## Project Structure Conventions

### Directory Layout
```
src/
├── <feature>/             # Feature-based modules (e.g. schools, workshops)
│   ├── __init__.py
│   ├── router.py         # FastAPI route definitions
│   ├── service.py        # Business logic
│   ├── models.py         # SQLAlchemy ORM model(s) for this feature
│   └── schemas.py        # Pydantic models for requests/responses
├── db/                    # Database infrastructure
│   ├── __init__.py       # Re-exports Base, get_engine, get_supabase
│   ├── base.py           # SQLAlchemy DeclarativeBase, engine, session factory
│   ├── client.py         # Supabase client and connection
│   ├── enums.py          # Shared PostgreSQL enum types
│   └── models.py         # Barrel re-export of ALL feature models (for Alembic)
├── storage/               # External storage
│   ├── __init__.py
│   └── s3_client.py      # AWS S3 client (boto3)
├── config.py             # Application configuration
├── exceptions.py          # Custom exception classes
├── models.py             # Shared Pydantic models and enums
└── main.py               # Application entry point

alembic/                   # Alembic migration environment
├── env.py                # Reads DATABASE_URL, imports Base.metadata
├── script.py.mako        # Migration template
└── versions/             # Auto-generated or hand-written migrations
```

#### Current Feature Modules
| Module | models.py contains | Description |
|--------|-------------------|-------------|
| `cycles/` | `Cycle`, `Cohort` | Temporal cycles and regional cohorts |
| `schools/` | `School`, `Contact`, `SchoolDateSelector` | School profiles, contacts, date preferences |
| `workshops/` | `Workshop`, `Webinar`, `WorkshopRegistration`, `WorkshopAsset`, `PortalMapping` | Workshop delivery pipeline |
| `sales/` | `Sale`, `Invoice` | Sales pipeline and invoicing |
| `assets/` | `Asset` | Content assets linked to workshops |
| `meetings/` | `OneOnOneMeeting` | 1-on-1 advisory meetings |
| `calendar/` | `PaulMartinCalendar` | Synced Google Calendar events |
| `settings/` | `Setting` | Application-level settings |

### Module Organization Pattern
Each feature module follows this consistent structure:
1. **`models.py`**: SQLAlchemy ORM models (table definitions)
2. **`schemas.py`**: Pydantic models for validation and serialization
3. **`service.py`**: Business logic and database operations
4. **`router.py`**: API endpoints (controllers)

## Coding Conventions

### 1. Import Organization
Follow this order (enforced by ruff/isort):
```python
# Standard library imports
import uuid
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

# Local application imports
from src.config import settings
from src.db import get_supabase
from src.exceptions import NotFoundException
from src.models import BaseResponse
```

### 2. Type Hints
- **Always use type hints** for function parameters and return values
- Use modern Python 3.12 syntax: `str | None` instead of `Optional[str]`
- Use `list[T]` and `dict[K, V]` instead of `List[T]` and `Dict[K, V]`
- Example:
```python
from supabase import Client

def get_task_by_id(task_id: str, supabase: Client) -> Task | None:
    """Get a task by ID."""
    result = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not result.data or len(result.data) == 0:
        return None
    return Task.model_validate(result.data[0])
```

### 3. Async/Await Pattern
- Use `async def` for FastAPI route handlers and any function that performs I/O (e.g. S3, HTTP).
- Supabase Python client is synchronous; use it in thread pool or from sync service layer, or wrap in `run_in_executor` if needed from async routes.
- Example:
```python
async def create_observation(observation_data: ObservationCreateRequest, supabase: Client) -> ObservationResponse:
    row = observation_data.model_dump()
    row["created_at"] = datetime.utcnow().isoformat()
    row["updated_at"] = row["created_at"]

    result = supabase.table("observations").insert(row).execute()
    if not result.data or len(result.data) == 0:
        raise ValueError("Insert failed")
    return ObservationResponse.model_validate(result.data[0])
```

### 4. Database Connection Management
Use dependency injection for the Supabase client:

**Pattern: Dependency Injection** (preferred for routers and services):
```python
@router.get("/{task_id}")
async def get_task_endpoint(
    task_id: str,
    supabase: Client = Depends(get_supabase)
) -> TaskResponse:
    task = get_task_by_id(task_id, supabase)
    if not task:
        raise NotFoundException(f"Task with ID {task_id} not found")
    return TaskResponse.model_validate(task)

# In service layer
def create_observation(data: ObservationCreateRequest, supabase: Client) -> Observation:
    result = supabase.table("observations").insert(data.model_dump()).execute()
    if not result.data:
        raise ValueError("Insert failed")
    return Observation.model_validate(result.data[0])
```

### 5. Supabase (PostgreSQL) Query Pattern
Use the Supabase client for table operations (PostgreSQL behind the API):
```python
from supabase import Client

# FIND ONE (by primary key or column)
result = supabase.table("tasks").select("*").eq("id", task_id).execute()
if not result.data or len(result.data) == 0:
    raise NotFoundException(f"Task with ID {task_id} not found")
task = result.data[0]

# FIND WITH FILTERS (and ordering, limit)
result = (
    supabase.table("tasks")
    .select("*")
    .eq("status", "open")
    .order("created_at", desc=True)
    .limit(10)
    .execute()
)
tasks = result.data or []

# INSERT
row = data.model_dump()
row["created_at"] = datetime.utcnow().isoformat()
row["updated_at"] = row["created_at"]
result = supabase.table("observations").insert(row).execute()
inserted = result.data[0] if result.data else None

# UPDATE
result = (
    supabase.table("tasks")
    .update({"status": TaskStatus.IN_PROGRESS, "updated_at": datetime.utcnow().isoformat()})
    .eq("id", task_id)
    .execute()
)
if not result.data or len(result.data) == 0:
    raise NotFoundException(f"Task with ID {task_id} not found")

# DELETE
result = supabase.table("tasks").delete().eq("id", task_id).execute()
if not result.data or len(result.data) == 0:
    raise NotFoundException(f"Task with ID {task_id} not found")
```

### 6. Router Definition Pattern
```python
from fastapi import APIRouter, Depends, status
from supabase import Client

router = APIRouter(prefix="/observations", tags=["Observations"])

@router.post("", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation_endpoint(
    observation_data: ObservationCreateRequest,
    supabase: Client = Depends(get_supabase),
) -> ObservationResponse:
    """Create a new observation."""
    return create_observation(observation_data, supabase)
```

**Key points**:
- Use descriptive endpoint function names with `_endpoint` suffix
- Always specify `response_model` and `status_code`
- Include docstrings
- Router prefix and tags defined at router level

### 7. Pydantic Schema Patterns

**Request Schemas**:
```python
class ObservationCreateRequest(BaseModel):
    task_id: str = Field(..., description="Associated task ID")
    notes: str = Field(..., min_length=1, description="Observation notes")
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Response Schemas**:
```python
from pydantic import BaseModel, ConfigDict

class ObservationResponse(BaseModel):
    id: str
    task_id: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
```

**Key points**:
- Use `Field()` with descriptions and validation
- Request models end with `Request`
- Response models end with `Response`
- List responses use pattern: `<Entity>ListResponse` with `total`, `page`, `limit`

### 8. SQLAlchemy 2.0 ORM Models

Each feature module has its own `models.py` with SQLAlchemy ORM classes. All models
inherit from `src.db.base.Base` (a `DeclarativeBase` subclass).

**Model file pattern** (`src/<feature>/models.py`):
```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Text, Uuid
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base


class MyEntity(Base):
    __tablename__ = "my_entities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("parents.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    parent: Mapped[Parent | None] = relationship(back_populates="children")

    __table_args__ = (
        Index("idx_my_entities_parent_id", "parent_id"),
    )
```

**Key conventions**:
- **`from __future__ import annotations`** at the top of every model file to enable lazy type evaluation and avoid circular imports across feature modules.
- **UUIDs** for all primary keys (`Uuid` column type, `default=uuid.uuid4`).
- **`Mapped[T]`** type hints with `mapped_column()` (SQLAlchemy 2.0 style).
- **`snake_case`** column names matching the PostgreSQL convention.
- **`TIMESTAMP(timezone=True)`** for all datetime columns.
- **`server_default`** for booleans and timestamps to ensure DB-level defaults.
- **Relationships** use string-based forward references (e.g. `Mapped[list[OtherModel]]`) — resolved at runtime by SQLAlchemy.
- **`ForeignKey("table_name.column")`** uses table name strings — no cross-module import needed.
- **Shared enums** live in `src/db/enums.py` and are imported where needed.
- **Computed columns** use `sqlalchemy.Computed(...)` for PostgreSQL `GENERATED ALWAYS AS ... STORED`.

**Barrel re-export** (`src/db/models.py`):
All feature models are re-exported from `src/db/models.py` so that Alembic and scripts
can import everything from a single location:
```python
from src.db.models import School, Cycle, Sale, ...
```

### 8b. Pydantic Schemas (Request/Response)

Pydantic models in `schemas.py` handle API validation and serialization — separate from
SQLAlchemy ORM models:
```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class SchoolResponse(BaseModel):
    id: str
    name: str
    city: str | None = None
    state: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
```

**Key points**:
- Pydantic schemas live in `<feature>/schemas.py`, SQLAlchemy models in `<feature>/models.py`.
- Use `from_attributes=True` in `model_config` to hydrate from ORM instances.
- Request models end with `Request`, response models end with `Response`.

### 9. Exception Handling

Use custom exceptions from `src/exceptions.py`:
```python
from src.exceptions import NotFoundException, ValidationException

# In service layer
if not task:
    raise NotFoundException(f"Task with ID {task_id} not found")

# In router (FastAPI handles HTTPException automatically)
from fastapi import HTTPException
raise HTTPException(status_code=400, detail="Invalid input")
```

**Available custom exceptions**:
- `BaseAPIException`: Base class for all custom exceptions
- `NotFoundException`: 404 errors
- `ValidationException`: 422 validation errors
- `AuthenticationException`: 401 auth errors

### 10. Configuration Management
All configuration is in `src/config.py` using Pydantic Settings:
```python
from src.config import settings

# Access settings
supabase_url = settings.supabase_url
supabase_key = settings.supabase_key
s3_bucket = settings.s3_bucket_name
debug_mode = settings.debug
```

**Key settings**:
- Supabase: `supabase_url`, `supabase_key` (anon or service role)
- AWS S3: `aws_access_key_id`, `aws_secret_access_key`, `aws_region`, `s3_bucket_name`
- Logging: `log_level`
- Environment: `environment`, `debug`

### 11. Logging
Use structlog throughout:
```python
import structlog

logger = structlog.get_logger()

# Logging examples
logger.info("Task created", task_id=task.id, title=task.title)
logger.error("Failed to process observation", error=str(e), observation_id=obs_id)
logger.debug("Search results", count=len(results), threshold=score_threshold)
```

### 12. Enum Definitions
Enums are in `src/models.py`:
```python
class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

**Usage**:
```python
task.status = TaskStatus.IN_PROGRESS
task.priority = TaskPriority.HIGH
```

### 13. File Upload Handling
Use FastAPI `UploadFile` for multipart uploads; store files in AWS S3 via your S3 client:
```python
from fastapi import File, Form, UploadFile

@router.post("/upload")
async def upload_endpoint(
    task_id: str = Form(...),
    images: list[UploadFile] = File(default_factory=list),
) -> UploadResponse:
    for image in images:
        file_bytes = await image.read()
        # Upload to S3 via src/storage/s3_client.py
```

### 14. Response Patterns

**Success Response**:
```python
# Supabase returns rows with id, created_at, updated_at; validate directly
return ObservationResponse.model_validate(result.data[0])
```

**List Response**:
```python
return ObservationListResponse(
    observations=[ObservationResponse.model_validate(o) for o in observations],
    total=total_count,
    page=pagination.page,
    limit=pagination.limit
)
```

**Error Response**: Let FastAPI handle via exceptions

### 15. Testing Conventions
Tests are in `tests/` directory:
- Use `pytest` and `pytest-asyncio` (if using async routes)
- Fixture definitions in `conftest.py`
- Test files: `test_*.py`
- Mock Supabase client or use a test project:
```python
import pytest
from supabase import create_client, Client

@pytest.fixture
def supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def test_create_observation(supabase_client: Client):
    result = supabase_client.table("observations").insert({"notes": "test"}).execute()
    assert result.data and len(result.data) > 0
```

## Best Practices

### 1. Separation of Concerns
- **Routers**: Only handle HTTP request/response, validation
- **Services**: Business logic, database operations
- **Schemas**: Data validation and serialization
- **Models**: Database structure

### 2. Error Handling
- Use custom exceptions for domain errors
- Let FastAPI handle validation errors
- Always provide meaningful error messages
- Include error context in logs

### 3. Database Operations
- **Supabase client** for simple REST-style queries: `.select()`, `.insert()`, `.update()`, `.delete()`, `.eq()`, `.order()`, `.limit()`.
- **SQLAlchemy ORM** for complex queries, joins, and transactions via `Session`.
- Check `result.data` and `len(result.data)` after Supabase execute; handle empty/not-found explicitly.
- Use RLS (Row Level Security) in Supabase for access control when appropriate.
- For file storage, use AWS S3 via boto3; generate presigned URLs for uploads/downloads when needed.

### 3b. Alembic Migrations
Schema changes are managed via Alembic (integrated with SQLAlchemy models):
```bash
# Auto-generate a migration from model changes
uv run alembic revision --autogenerate -m "add_new_column_to_schools"

# Apply migrations (use session pooler port 5432 for Supabase)
DATABASE_URL="postgresql://...@pooler.supabase.com:5432/postgres" uv run alembic upgrade head

# Downgrade one step
uv run alembic downgrade -1
```
- The `alembic/env.py` reads `DATABASE_URL` from `src.config.settings` and imports `Base.metadata` via `src.db.models`.
- **Always review** auto-generated migrations before applying — especially `DROP` statements.
- For long-running DDL against Supabase, use the **session pooler** (port `5432`), not the transaction pooler (port `6543`).

### 4. API Design
- Use proper HTTP methods (GET, POST, PUT, DELETE)
- Use appropriate status codes
- Include pagination for list endpoints
- Use query parameters for filters
- Use path parameters for resource IDs

### 5. Validation
- Validate at the Pydantic schema level
- Use Field() constraints (min_length, ge, le, etc.)
- Validate business rules in service layer
- Return clear validation error messages

### 6. Documentation
- Include docstrings for all public functions
- Document complex business logic
- Keep API documentation up to date (FastAPI auto-generates from docstrings)

### 7. Code Quality
- Line length: 100 characters (ruff configuration)
- Follow PEP 8 naming conventions
- Use descriptive variable names
- Keep functions focused and small

## Common Patterns

### Creating a New Feature Module
1. Create directory: `src/<feature_name>/`
2. Create files: `__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`
3. Define SQLAlchemy ORM model(s) in `models.py` (inherit from `src.db.base.Base`, use `from __future__ import annotations`)
4. Add model re-exports to `src/db/models.py` (barrel file) so Alembic can discover them
5. Generate Alembic migration: `uv run alembic revision --autogenerate -m "add_<feature>_table"`
6. Define Pydantic request/response schemas in `schemas.py`
7. Implement service functions in `service.py`
8. Create API endpoints in `router.py`
9. Register router in `src/main.py`

### Adding a New Endpoint
```python
# 1. Define SQLAlchemy model in <feature>/models.py (if new table needed)
# 2. Define request/response schemas in <feature>/schemas.py
class MyRequest(BaseModel):
    field: str = Field(...)

class MyResponse(BaseModel):
    id: str
    field: str
    model_config = ConfigDict(from_attributes=True)

# 3. Implement service function in service.py
def my_service_function(data: MyRequest, supabase: Client) -> MyEntity:
    result = supabase.table("my_table").insert(data.model_dump()).execute()
    if not result.data:
        raise ValueError("Insert failed")
    return MyEntity.model_validate(result.data[0])

# 4. Create endpoint in router.py
@router.post("", response_model=MyResponse)
async def my_endpoint(
    data: MyRequest,
    supabase: Client = Depends(get_supabase)
) -> MyResponse:
    """Endpoint description."""
    result = my_service_function(data, supabase)
    return MyResponse.model_validate(result)
```

### Adding Database Indexes
In Supabase (PostgreSQL), create indexes via SQL in the Supabase SQL editor or migrations:
```sql
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_observations_task_id ON observations(task_id);
```

## Development Workflow

### Running the Application
```bash
# Development mode (from root)
python main.py

# Or with uvicorn directly
uvicorn src.main:app --reload --port 8100
```

### Running Tests
```bash
pytest
pytest tests/test_specific.py
pytest -v  # verbose
pytest --asyncio-mode=auto
```

### Database Setup
```bash
# Supabase: create project at supabase.com, get SUPABASE_URL, SUPABASE_KEY, DATABASE_URL
# AWS: create S3 bucket, set IAM credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

# Apply schema migrations via Alembic
uv run alembic upgrade head

# Auto-generate migration after model changes
uv run alembic revision --autogenerate -m "describe_the_change"
```

### Code Formatting
```bash
# Format with black
black src/ tests/

# Sort imports
isort src/ tests/

# Lint with ruff
ruff check src/ tests/
```

## Key Files Reference

- **`src/main.py`**: Application initialization, middleware, exception handlers
- **`src/config.py`**: Configuration (Supabase URL/key, DATABASE_URL, AWS, env)
- **`src/models.py`**: Shared enums and base Pydantic models
- **`src/exceptions.py`**: Custom exception classes
- **`src/db/base.py`**: SQLAlchemy `DeclarativeBase`, engine factory, session factory
- **`src/db/enums.py`**: Shared PostgreSQL enum types (SalesStatus, ProposalType, etc.)
- **`src/db/models.py`**: Barrel re-export of all SQLAlchemy models (used by Alembic)
- **`src/db/client.py`**: Supabase client and `get_supabase` dependency
- **`src/storage/s3_client.py`**: AWS S3 client (boto3)
- **`alembic/env.py`**: Alembic migration environment (reads DATABASE_URL, Base.metadata)
- **`pyproject.toml`**: Project dependencies and tool configuration

## Environment Variables
Required in `.env` file:
```
# Supabase (PostgreSQL)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket

# App
LOG_LEVEL=INFO
DEBUG=false
ENVIRONMENT=development
```

## Additional Notes

### Supabase (PostgreSQL)
- Client: `src/db/client.py` — create with `create_client(SUPABASE_URL, SUPABASE_KEY)`.
- Use `.table("table_name")` for CRUD; `.select()`, `.insert()`, `.update()`, `.delete()`, `.eq()`, `.order()`, `.limit()`.
- Use Supabase Auth, RLS, and Storage from the same project if needed.

### SQLAlchemy 2.0
- `src/db/base.py` — `Base` (DeclarativeBase), `get_engine()`, `get_session_factory()`.
- Each feature module has `models.py` with ORM classes inheriting from `Base`.
- All models are re-exported in `src/db/models.py` (barrel) for Alembic auto-detection.
- Use `from __future__ import annotations` in every model file to avoid circular imports.
- Use `Mapped[T]` + `mapped_column()` (not legacy `Column()`).
- Relationships across feature modules use string class names — SQLAlchemy resolves them at configure time.

### Alembic Migrations
- Config: `alembic.ini` + `alembic/env.py`.
- `env.py` reads `DATABASE_URL` from `src.config.settings` and sets `target_metadata = Base.metadata`.
- For Supabase, use session pooler (port `5432`) for DDL migrations, not transaction pooler (port `6543`).

### AWS S3 Storage
- Client: `src/storage/s3_client.py` (boto3).
- Use for: file uploads (images, documents), static assets.
- Generate presigned URLs for client uploads or direct uploads when appropriate.

## Troubleshooting Common Issues

1. **Import errors**: Check `__init__.py` exports under `src/` and that imports use the `src.` prefix.
2. **Supabase connection**: Verify `SUPABASE_URL` and `SUPABASE_KEY`; check project status in Supabase dashboard.
3. **Empty result**: After `.execute()`, check `result.data` and `len(result.data)` before indexing.
4. **Type errors**: Use Pydantic `model_validate()` for Supabase row dicts.
5. **S3 access**: Verify IAM credentials and bucket name; check CORS if using presigned URLs from the frontend.
6. **RLS**: If rows are missing, check Supabase Row Level Security policies.

---

**Remember**: This is a FastAPI application using **Supabase (PostgreSQL)**, **SQLAlchemy 2.0** (ORM + Alembic migrations), and **AWS S3**. Use SQLAlchemy models in each feature's `models.py`, Pydantic schemas in `schemas.py`, the Supabase client or SQLAlchemy Session for database operations, boto3 for S3, and follow the established module structure.
