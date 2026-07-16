"""ConsumptionProfile model — stores historical consumption data."""

from sqlalchemy import Column, String, Float, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class ConsumptionProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "consumption_profiles"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    quantity_sold = Column(Float, nullable=False, default=0.0)
    quantity_ordered = Column(Float, nullable=False, default=0.0)
    seasonality_factor = Column(Float, nullable=True)
    trend = Column(String(50), nullable=True)

    product = relationship("Product", lazy="selectin")
    store = relationship("Store", lazy="selectin")