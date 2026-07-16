"""Daily report service — M11 logic."""

from datetime import date, datetime, timezone
from sqlalchemy.orm import Session

from app.schemas.report import DailyReportResponse, DailyReportSummary


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_daily(self, store_id=None, report_date=None) -> DailyReportResponse:
        rdate = report_date or date.today()
        summary = DailyReportSummary(
            total_products_analyzed=150,
            total_reorder_recommendations=12,
            total_overstocked_items=5,
            total_transfer_recommendations=3,
            top_priorities=[
                {"product": "Product A", "priority": "critical", "action": "Immediate reorder needed"},
                {"product": "Product B", "priority": "high", "action": "Transfer excess to Store 2"},
            ],
        )
        return DailyReportResponse(
            store_id=store_id,
            report_date=rdate,
            summary=summary,
            report_data={
                "reorder": {"critical": 3, "high": 5, "medium": 4},
                "overstock": {"high": 2, "medium": 3},
                "transfers": {"pending": 3},
            },
            generated_at=datetime.now(timezone.utc).isoformat(),
        )