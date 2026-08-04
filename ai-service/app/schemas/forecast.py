"""Forecast schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ForecastRequest(BaseModel):
    product_id: UUID
    store_id: UUID
    horizon_days: int = 30
    geolocate: str | None = None  # e.g. "Hanoi, Vietnam" — supplied by main BE
    localtime: str | None = None  # e.g. "2026-07-17T10:00:00+07:00" — supplied by main BE


class ForecastPoint(BaseModel):
    date: date
    predicted_quantity: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class NewsContextItem(BaseModel):
    title: str
    url: str | None = None
    published_date: str | None = None
    relevance_score: float | None = None  # 0.0–1.0 how relevant to this forecast


class NewsAnalysisResult(BaseModel):
    """Structured output from the LLM news analysis."""
    sentiment_score: float  # -1.0 to 1.0
    demand_adjustment: float  # multiplier (e.g. 1.15)
    confidence_adjustment: float  # extra margin (e.g. 0.05)
    affected_categories: list[str] = []
    explanation: str = ""
    action_window_days: int | None = None


class ForecastResponse(BaseModel):
    product_id: UUID
    store_id: UUID
    forecast: list[ForecastPoint]
    model_used: str | None = None
    confidence_level: float | None = None
    geolocate: str | None = None
    localtime: str | None = None
    news_context: list[NewsContextItem] | None = None
    news_sentiment_score: float | None = None  # -1.0 (negative) to +1.0 (positive)
    news_adjustment_factor: float | None = None  # multiplier applied to base demand