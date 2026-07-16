"""Explanation model — stores AI-generated explanations for recommendations."""

from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class Explanation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "explanations"

    explainable_type = Column(String(50), nullable=False)
    explainable_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    confidence = Column(String(20), nullable=True)
    model_used = Column(String(100), nullable=True)
    metadata_json = Column(JSON, nullable=True)