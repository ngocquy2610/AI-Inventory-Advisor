"""Supplier reliability schemas."""

from uuid import UUID

from pydantic import BaseModel


class SupplierReliabilityRequest(BaseModel):
    supplier_id: UUID | None = None


class SupplierReliabilityResult(BaseModel):
    supplier_id: UUID
    supplier_name: str | None = None
    on_time_delivery_rate: float | None = None
    quality_score: float | None = None
    lead_time_days: float | None = None
    lead_time_variability: float | None = None
    fill_rate: float | None = None
    overall_reliability_score: float | None = None
    risk_level: str | None = None


class SupplierReliabilityResponse(BaseModel):
    suppliers: list[SupplierReliabilityResult]
    total_items: int