"""Overstock detection schemas — M4 batch output + API models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Input-side models (for loader validation) ────────────────────────

class ConsumptionProfile(BaseModel):
    """Subset of M1 fields that M4 consumes for velocity."""
    product_id: str
    store_id: str
    average_daily_sales: float
    moving_average_7: float | None = None
    trend: str | None = None


class ProductStoreStock(BaseModel):
    """A single row from product_store_stock (live stock table)."""
    product_id: str
    store_id: str
    current_stock: float
    updated_at: datetime


class Product(BaseModel):
    """A single row from products (catalog table)."""
    id: str
    category: str


class ClassificationRow(BaseModel):
    """A single row from M5 classification output."""
    product_id: str
    store_id: str
    tier: str | None = None
    insufficient_data: bool = False


# ── Output models ────────────────────────────────────────────────────

class OverstockFlag(BaseModel):
    """Single overstock flag — maps to a row in overstock_flags table."""
    product_id: str
    store_id: str
    category: str
    current_stock: float
    average_daily_sales: float
    days_of_supply: float | None = Field(
        ..., description="null when avg_daily_sales == 0 (dead stock / zero velocity)"
    )
    risk_level: str = Field(
        ..., description="high | medium | low | dead_zero_velocity"
    )
    suggested_action: str | None = Field(
        ..., description="flash_sale | discount | null (low risk)"
    )
    tier: str | None = Field(
        ..., description="M5 velocity tier, null if insufficient_data"
    )
    stock_data_stale: bool = False
    insufficient_data: bool = False
    computed_at: datetime


class OverstockRunMeta(BaseModel):
    """Metadata wrapper for batch output."""
    source_files: list[str] = [
        "data/module1_output.json",
        "data/module1_input.json",
        "data/module5_output.json",
    ]
    threshold_config_version: str = "2026-07-17"
    total_evaluated: int = 0
    total_flagged_medium: int = 0
    total_flagged_high: int = 0
    total_skipped_insufficient_data: int = 0
    total_skipped_missing_stock: int = 0
    total_skipped_missing_consumption: int = 0
    total_skipped_zero_stock: int = 0
    total_dead_zero_velocity: int = 0
    computed_at: datetime


class OverstockOutput(BaseModel):
    """Top-level output shape written to module4_output.json."""
    overstock_flags: list[OverstockFlag]
    meta: OverstockRunMeta


# ── Request / Response schemas for API ───────────────────────────────

class OverstockRunResponse(BaseModel):
    """Response from POST /api/v1/overstock/run."""
    success: bool = True
    meta: OverstockRunMeta


class OverstockQueryParams(BaseModel):
    """Query parameters for GET /api/v1/overstock."""
    store_id: str | None = None
    risk_level: str | None = None
    category: str | None = None


class OverstockApiFlag(BaseModel):
    """Single flag returned via API (mirrors OverstockFlag)."""
    product_id: str
    store_id: str
    category: str
    current_stock: float
    average_daily_sales: float
    days_of_supply: float | None
    risk_level: str
    suggested_action: str | None
    tier: str | None
    stock_data_stale: bool
    insufficient_data: bool
    computed_at: datetime


class OverstockApiResponse(BaseModel):
    """Response from GET /api/v1/overstock."""
    flags: list[OverstockApiFlag]
    total: int


# ── Legacy models (kept for backward compatibility) ──────────────────

from uuid import UUID  # noqa: F811


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