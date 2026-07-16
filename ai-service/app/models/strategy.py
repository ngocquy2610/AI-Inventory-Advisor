"""Strategy model — consolidated inventory strategy."""

from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class Strategy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "strategies"

    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    strategy_type = Column(String(50), nullable=False)  # reorder, transfer, pricing, promotion
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    action_items = Column(JSON, nullable=True)
    expected_impact = Column(JSON, nullable=True)
    priority = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    metadata_json = Column(JSON, nullable=True)

    store = relationship("Store", lazy="selectin")