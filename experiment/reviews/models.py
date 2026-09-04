"""
experiment/reviews/models.py
----------------------------
Phase 7: PostgreSQL ORM Models for Shopify App Reviews.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from experiment.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Review(Base):
    """Individual merchant review for a Shopify app."""

    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_app_id", "app_id"),
        Index("ix_reviews_app_slug", "app_slug"),
        Index("ix_reviews_rating", "rating"),
        Index("ix_reviews_review_date", "review_date"),
        Index("ix_reviews_fingerprint", "review_fingerprint", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=True,
    )
    app_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    review_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewer_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time_spent_using_app: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    app: Mapped[Any] = relationship("App", foreign_keys=[app_id])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "app_slug": self.app_slug,
            "reviewer_name": self.reviewer_name,
            "reviewer_location": self.reviewer_location,
            "time_spent_using_app": self.time_spent_using_app,
            "rating": self.rating,
            "review_date": self.review_date,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReviewCollectionRun(Base):
    """Audit log for review collection batch execution."""

    __tablename__ = "review_collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    apps_requested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    apps_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reviews_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReviewCollectionItem(Base):
    """Per-app audit log for review collection."""

    __tablename__ = "review_collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("review_collection_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    reviews_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_scraped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
