"""M1 — POST /api/v1/consumption/analyze"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.consumption import ConsumptionAnalysisRequest, ConsumptionAnalysisResponse
from app.services.consumption_service import ConsumptionService

router = APIRouter(prefix="/consumption", tags=["consumption"], dependencies=[Depends(verify_internal_token)])


@router.post("/analyze", response_model=ConsumptionAnalysisResponse)
def analyze_consumption(request: ConsumptionAnalysisRequest, db: Session = Depends(get_db)):
    service = ConsumptionService(db)
    return service.analyze(
        product_id=request.product_id,
        store_id=request.store_id,
        start_date=request.start_date,
        end_date=request.end_date,
    )