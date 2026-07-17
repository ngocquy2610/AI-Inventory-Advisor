"""Classification schemas — M5 velocity tiers + existing ABC/XYZ."""

from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, Field


# ── M5 Velocity Classification Schemas ──────────────────────────────

class ConsumptionMetric(BaseModel):
    """Subset of M1 fields that M5 actually consumes.

    This is the boundary for M1→M5 data passing. Only these fields
    cross into the classification service — M1's 'classification' block
    is explicitly excluded (see README decision note).
    """
    product_id: str
    store_id: str
    average_daily_sales: float
    days_with_sales: int
    last_sale_date: date
    trend: str | None = None
    analysis_period_end: date


class ClassificationResult(BaseModel):
    """Single product-store velocity tier output.

    Maps onto the product_classifications DB table (tier + computed_at
    persisted; previous_tier / tier_changed derivable at query time).
    """
    product_id: str
    store_id: str
    category: str
    tier: str | None = Field(
        ..., description="Velocity tier: fast | medium | slow | dead | null (insufficient_data)"
    )
    previous_tier: str | None = None
    tier_changed: bool = False
    insufficient_data: bool = False
    days_since_last_sale: int
    average_daily_sales: float
    computed_at: datetime


class ClassificationBatchMeta(BaseModel):
    """Metadata wrapper for batch output."""
    source_file: str
    thresholds_version: str = "2026-07-17"
    total_classified: int
    total_insufficient_data: int


class ClassificationBatchOutput(BaseModel):
    """Top-level output shape written to module5_output.json."""
    classifications: list[ClassificationResult]
    meta: ClassificationBatchMeta


# ── Existing ABC/XYZ Schemas (unchanged) ────────────────────────────

from uuid import UUID  # noqa: F811 — needed only by existing schemas below


class ClassificationRequest(BaseModel):
    product_id: UUID | None = None
    store_id: UUID | None = None


class ClassificationABCXYZResult(BaseModel):
    product_id: UUID
    store_id: UUID
    product_name: str | None = None
    abc_class: str | None = None
    xyz_class: str | None = None
    is_perishable: bool = False
    lead_time_category: str | None = None


class ClassificationResponse(BaseModel):
    classifications: list[ClassificationABCXYZResult]
    total_items: int
