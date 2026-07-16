"""Consumption analysis schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ConsumptionAnalysisRequest(BaseModel):
    product_id: UUID
    store_id: UUID
    start_date: date
    end_date: date


class ConsumptionMetric(BaseModel):
    period: str
    total_sold: float
    average_daily: float
    seasonality_factor: float | None = None
    trend: str | None = None


class ConsumptionAnalysisResponse(BaseModel):
    product_id: UUID
    store_id: UUID
    metrics: list[ConsumptionMetric]
    total_consumption: float
    average_daily_consumption: float
    trend_direction: str | None = None