"""
experiment/db/init_db.py
------------------------
Idempotent database and table initialization script for AppScout.

Ensures the PostgreSQL database exists and initializes all required tables
(apps, categories, app_categories, ingestion_runs, ingestion_items).
"""

from __future__ import annotations

import argparse
import logging
import sys
from urllib.parse import urlparse

from psycopg import sql
import psycopg
from sqlalchemy import text

from .database import Base, check_connection, get_database_url, get_engine
from .models import App, AppCategory, Category, IngestionItem, IngestionRun

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def ensure_database_exists(db_url: str) -> None:
    """Check if the target PostgreSQL database exists; create it if missing."""
    # Convert postgresql+psycopg:// to postgresql:// for raw psycopg connection
    clean_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(clean_url)
    target_dbname = parsed.path.lstrip("/")

    if not target_dbname:
        return

    # Connect to default 'postgres' database to check target database existence
    admin_url = f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 5432}/postgres"

    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_dbname,))
                exists = cur.fetchone()
                if not exists:
                    logger.info("Database '%s' does not exist. Creating...", target_dbname)
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
                    logger.info("Database '%s' created successfully.", target_dbname)
                else:
                    logger.debug("Database '%s' already exists.", target_dbname)
    except Exception as exc:
        logger.warning(
            "Could not verify/create database '%s' via admin connection: %s. Assuming database is already created.",
            target_dbname,
            exc,
        )


def init_database(*, drop_tables: bool = False) -> bool:
    """Initialize all PostgreSQL tables idempotently."""
    db_url = get_database_url()
    ensure_database_exists(db_url)

    engine = get_engine()

    if drop_tables:
        logger.warning("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped.")

    logger.info("Creating all tables in PostgreSQL if not already present...")
    Base.metadata.create_all(bind=engine)
    logger.info("Schema initialized successfully.")

    # Verify tables
    with engine.connect() as conn:
        res = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
            )
        )
        tables = [row[0] for row in res.fetchall()]
        logger.info("Verified public tables in database: %s", ", ".join(tables))

    return True


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for database initialization."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="python -m experiment.db.init_db",
        description="Initialize AppScout PostgreSQL schema and tables.",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before recreating schema (WARNING: Destructive).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    print("\n" + "=" * 76)
    print("APPSCOUT - POSTGRESQL SCHEMA INITIALIZATION")
    print("=" * 76)

    db_url = get_database_url()
    ensure_database_exists(db_url)

    ok, conn_msg = check_connection()
    if not ok:
        print(f"\n[ERROR] {conn_msg}", file=sys.stderr)
        print("\nPlease verify your PostgreSQL server is running and .env contains valid credentials:\n")
        print("  DATABASE_URL=postgresql+psycopg://<username>:<password>@localhost:5432/<dbname>\n")
        return 1

    print(f"[OK] {conn_msg}")

    try:
        init_database(drop_tables=args.drop)
        print("[OK] All PostgreSQL tables initialized successfully (apps, categories, app_categories, ingestion_runs, ingestion_items).")
        print("=" * 76 + "\n")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Schema initialization failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
