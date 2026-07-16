"""SupplierReliability model — supplier performance tracking."""

from sqlalchemy import Column, String, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class SupplierReliability(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "supplier_reliabilities"

    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, index=True)
    on_time_delivery_rate = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    lead_time_days = Column(Float, nullable=True)
    lead_time_variability = Column(Float, nullable=True)
    fill_rate = Column(Float, nullable=True)
    overall_reliability_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    recommendations = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    supplier = relationship("Supplier", lazy="selectin")