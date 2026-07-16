"""Transfer recommendation schemas."""

from uuid import UUID

from pydantic import BaseModel


class TransferRequest(BaseModel):
    product_id: UUID | None = None
    from_store_id: UUID | None = None
    to_store_id: UUID | None = None


class TransferItem(BaseModel):
    product_id: UUID
    product_name: str | None = None
    from_store_id: UUID
    to_store_id: UUID
    quantity: float
    reason: str | None = None
    priority: str | None = None


class TransferResponse(BaseModel):
    recommendations: list[TransferItem]
    total_items: int