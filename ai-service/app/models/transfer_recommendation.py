"""TransferRecommendation model — suggests stock transfers between stores."""

from sqlalchemy import Column, String, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class TransferRecommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transfer_recommendations"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    from_store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    to_store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    reason = Column(String(500), nullable=True)
    priority = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    metadata_json = Column(JSON, nullable=True)

    product = relationship("Product", lazy="selectin")
    from_store = relationship("Store", foreign_keys=[from_store_id], lazy="selectin")
    to_store = relationship("Store", foreign_keys=[to_store_id], lazy="selectin")