"""ReorderRecommendation model — suggested reorder quantities."""

from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class ReorderRecommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reorder_recommendations"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    recommended_quantity = Column(Float, nullable=False)
    current_stock = Column(Float, nullable=False, default=0.0)
    reorder_point = Column(Float, nullable=True)
    economic_order_quantity = Column(Float, nullable=True)
    priority = Column(String(20), nullable=True)  # critical, high, medium, low
    reason = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    product = relationship("Product", lazy="selectin")
    store = relationship("Store", lazy="selectin")