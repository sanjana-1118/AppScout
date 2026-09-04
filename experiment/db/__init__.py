"""
experiment.db
-------------
PostgreSQL persistence package for AppScout.

Provides SQLAlchemy models, engine configuration, session management,
and repository functions for persisting apps, categories, and ingestion runs.
"""

from .database import (
    Base,
    SessionLocal,
    check_connection,
    get_db,
    get_engine,
)
from .models import (
    App,
    AppCategory,
    Category,
    IngestionItem,
    IngestionRun,
)

__all__ = [
    "Base",
    "SessionLocal",
    "get_engine",
    "get_db",
    "check_connection",
    "App",
    "Category",
    "AppCategory",
    "IngestionRun",
    "IngestionItem",
]
