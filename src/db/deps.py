"""SQLAlchemy session dependency for FastAPI."""

from typing import Annotated, Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from src.db.base import get_session_factory


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]
