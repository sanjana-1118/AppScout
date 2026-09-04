"""
experiment/db/models.py
-----------------------
SQLAlchemy Declarative ORM models for AppScout.

Defines schemas for:
- apps: Canonical app listings and metadata.
- categories: Normalized category hierarchy records.
- app_categories: Many-to-many relationship mapping between apps and categories.
- ingestion_runs: Execution logs for automated ingestion pipelines.
- ingestion_items: Per-app status tracking for an ingestion run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Return timezone-aware current UTC timestamp."""
    return datetime.now(timezone.utc)


class App(Base):
    """Canonical Shopify App Store application record."""

    __tablename__ = "apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    app_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    developer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    pricing_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    free_trial_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    first_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    categories: Mapped[list[Category]] = relationship(
        "Category",
        secondary="app_categories",
        back_populates="apps",
        lazy="selectin",
    )
    pricing_plans: Mapped[list[AppPricingPlan]] = relationship(
        "AppPricingPlan",
        back_populates="app",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_slug": self.app_slug,
            "app_name": self.app_name,
            "app_url": self.app_url,
            "developer_name": self.developer_name,
            "description": self.description,
            "average_rating": float(self.average_rating) if self.average_rating is not None else None,
            "review_count": self.review_count,
            "first_discovered_at": self.first_discovered_at.isoformat() if self.first_discovered_at else None,
            "last_scraped_at": self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "categories": [c.slug for c in self.categories],
        }


class Category(Base):
    """Normalized Shopify App Store category record."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    apps: Mapped[list[App]] = relationship(
        "App",
        secondary="app_categories",
        back_populates="categories",
        lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AppCategory(Base):
    """Many-to-many association table linking apps and categories."""

    __tablename__ = "app_categories"
    __table_args__ = (
        UniqueConstraint("app_id", "category_id", name="uq_app_category"),
    )

    app_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("apps.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IngestionRun(Base):
    """High-level batch ingestion execution tracking record."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    apps_requested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    apps_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    apps_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    apps_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    apps_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    snapshots_reused: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_http_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    items: Mapped[list[IngestionItem]] = relationship(
        "IngestionItem",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "apps_requested": self.apps_requested,
            "apps_processed": self.apps_processed,
            "apps_succeeded": self.apps_succeeded,
            "apps_failed": self.apps_failed,
            "apps_skipped": self.apps_skipped,
            "snapshots_reused": self.snapshots_reused,
            "new_http_requests": self.new_http_requests,
            "notes": self.notes,
        }


class IngestionItem(Base):
    """Per-app processing log and status record associated with an ingestion run."""

    __tablename__ = "ingestion_items"
    __table_args__ = (
        Index("ix_ingestion_items_run_slug", "ingestion_run_id", "app_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    app_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    app_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    run: Mapped[IngestionRun] = relationship(
        "IngestionRun",
        back_populates="items",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ingestion_run_id": self.ingestion_run_id,
            "app_slug": self.app_slug,
            "app_url": self.app_url,
            "status": self.status,
            "error_message": self.error_message,
            "snapshot_path": self.snapshot_path,
            "result_path": self.result_path,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AppPricingPlan(Base):
    """Normalized pricing plan tier for a Shopify application."""

    __tablename__ = "app_pricing_plans"
    __table_args__ = (
        Index("ix_pricing_plans_app_id", "app_id"),
        Index("ix_pricing_plans_app_slug", "app_slug"),
        Index("ix_pricing_plans_price", "price_amount"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(50), default="monthly", nullable=False)
    free_trial_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    app: Mapped[App] = relationship(
        "App",
        back_populates="pricing_plans",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "app_slug": self.app_slug,
            "plan_name": self.plan_name,
            "price_amount": float(self.price_amount) if self.price_amount is not None else None,
            "currency": self.currency,
            "billing_interval": self.billing_interval,
            "free_trial_days": self.free_trial_days,
            "features": self.features,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
