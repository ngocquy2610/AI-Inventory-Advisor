"""Forecast model — stores demand forecast results."""

from sqlalchemy import Column, String, Float, Date, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class Forecast(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "forecasts"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    predicted_quantity = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    confidence_level = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    product = relationship("Product", lazy="selectin")
    store = relationship("Store", lazy="selectin")