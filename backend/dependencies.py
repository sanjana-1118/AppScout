"""
backend/dependencies.py
-----------------------
FastAPI dependency injection utilities for AppScout.
Provides database sessions and reusable pagination / query dependencies.
"""

from __future__ import annotations

from typing import Generator
from fastapi import Query
from sqlalchemy.orm import Session

from experiment.db.database import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional SQLAlchemy database session to route handlers."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class PaginationParams:
    """Common pagination parameters for list endpoints."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number, 1-indexed"),
        limit: int = Query(20, ge=1, le=250, description="Items per page (max 250)"),
    ):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit
