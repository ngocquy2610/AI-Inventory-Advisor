"""OverstockFlag model — flags products with excess inventory."""

from sqlalchemy import Column, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class OverstockFlag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "overstock_flags"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    current_quantity = Column(Float, nullable=False, default=0.0)
    suggested_max = Column(Float, nullable=True)
    excess_quantity = Column(Float, nullable=True)
    days_of_cover = Column(Float, nullable=True)
    is_overstocked = Column(Boolean, nullable=False, default=False)
    severity = Column(String(20), nullable=True)  # low, medium, high, critical
    action = Column(String(200), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    product = relationship("Product", lazy="selectin")
    store = relationship("Store", lazy="selectin")