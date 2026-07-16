"""Reorder recommendation schemas."""

from uuid import UUID

from pydantic import BaseModel


class ReorderRequest(BaseModel):
    product_id: UUID | None = None
    store_id: UUID | None = None


class ReorderItem(BaseModel):
    product_id: UUID
    store_id: UUID
    product_name: str | None = None
    current_stock: float = 0.0
    recommended_quantity: float
    reorder_point: float | None = None
    economic_order_quantity: float | None = None
    priority: str | None = None
    reason: str | None = None


class ReorderResponse(BaseModel):
    recommendations: list[ReorderItem]
    total_items: int