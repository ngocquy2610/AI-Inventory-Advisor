"""Base model with common columns (id, timestamps)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class TimestampMixin:
    """Mixin adding created_at / updated_at columns."""

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class UUIDMixin:
    """Mixin adding a UUID primary key."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)