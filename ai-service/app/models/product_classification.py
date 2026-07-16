"""ProductClassification model — ABC/XYZ classification results."""

from sqlalchemy import Column, String, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import UUIDMixin, TimestampMixin


class ProductClassification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "product_classifications"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    abc_class = Column(String(1), nullable=True)  # A, B, C
    xyz_class = Column(String(1), nullable=True)  # X, Y, Z
    is_perishable = Column(Boolean, nullable=False, default=False)
    lead_time_category = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    product = relationship("Product", lazy="selectin")
    store = relationship("Store", lazy="selectin")