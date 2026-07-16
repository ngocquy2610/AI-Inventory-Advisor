"""Overstock detection schemas."""

from uuid import UUID

from pydantic import BaseModel


class OverstockRequest(BaseModel):
    product_id: UUID | None = None
    store_id: UUID | None = None


class OverstockItem(BaseModel):
    product_id: UUID
    store_id: UUID
    product_name: str | None = None
    current_quantity: float = 0.0
    suggested_max: float | None = None
    excess_quantity: float | None = None
    days_of_cover: float | None = None
    is_overstocked: bool = False
    severity: str | None = None
    action: str | None = None


class OverstockResponse(BaseModel):
    overstocked_items: list[OverstockItem]
    total_overstocked: int