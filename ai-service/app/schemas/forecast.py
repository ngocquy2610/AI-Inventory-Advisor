"""Forecast schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ForecastRequest(BaseModel):
    product_id: UUID
    store_id: UUID
    horizon_days: int = 30


class ForecastPoint(BaseModel):
    date: date
    predicted_quantity: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResponse(BaseModel):
    product_id: UUID
    store_id: UUID
    forecast: list[ForecastPoint]
    model_used: str | None = None
    confidence_level: float | None = None