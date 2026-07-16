"""Classification schemas."""

from uuid import UUID

from pydantic import BaseModel


class ClassificationRequest(BaseModel):
    product_id: UUID | None = None
    store_id: UUID | None = None


class ClassificationResult(BaseModel):
    product_id: UUID
    store_id: UUID
    product_name: str | None = None
    abc_class: str | None = None
    xyz_class: str | None = None
    is_perishable: bool = False
    lead_time_category: str | None = None


class ClassificationResponse(BaseModel):
    classifications: list[ClassificationResult]
    total_items: int