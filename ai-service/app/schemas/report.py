"""Report schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class DailyReportRequest(BaseModel):
    store_id: UUID | None = None
    report_date: date | None = None


class DailyReportSummary(BaseModel):
    total_products_analyzed: int
    total_reorder_recommendations: int
    total_overstocked_items: int
    total_transfer_recommendations: int
    top_priorities: list[dict] = []


class DailyReportResponse(BaseModel):
    store_id: UUID | None
    report_date: date
    summary: DailyReportSummary
    report_data: dict
    generated_at: str