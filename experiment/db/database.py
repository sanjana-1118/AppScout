"""
experiment/db/database.py
-------------------------
PostgreSQL database engine and session management for AppScout.

Loads configuration from environment variables (.env), configures SQLAlchemy
with psycopg (v3) driver, and exposes thread-safe session factories.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

# Load .env variables
load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/appscout"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models in AppScout."""
    pass


def get_database_url() -> str:
    """Retrieve the PostgreSQL connection URL from the environment."""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    # Ensure postgresql+psycopg driver scheme if standard postgres:// or postgresql:// is provided
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the global SQLAlchemy Engine instance (lazy singleton)."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))

        logger.debug("Creating SQLAlchemy engine for URL: %s", db_url.split("@")[-1])
        _engine = create_engine(
            db_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the global SQLAlchemy session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionFactory


def SessionLocal() -> Session:
    """Instantiate a new SQLAlchemy session."""
    factory = get_session_factory()
    return factory()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for acquiring and safely releasing a database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection() -> tuple[bool, str]:
    """Test connection to the PostgreSQL database.

    Returns
    -------
    (is_connected, message) : tuple[bool, str]
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version_str = result.scalar()
            return True, f"Connected to PostgreSQL: {version_str}"
    except Exception as exc:
        return False, f"PostgreSQL connection failed: {exc}"
