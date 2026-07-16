"""M11 — POST /api/v1/report/daily"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.report import DailyReportRequest, DailyReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/report", tags=["report"], dependencies=[Depends(verify_internal_token)])


@router.post("/daily", response_model=DailyReportResponse)
def generate_daily_report(request: DailyReportRequest, db: Session = Depends(get_db)):
    service = ReportService(db)
    return service.generate_daily(store_id=request.store_id, report_date=request.report_date)