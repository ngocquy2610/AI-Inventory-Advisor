"""M4 — POST /api/v1/overstock/detect"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.overstock import OverstockRequest, OverstockResponse
from app.services.overstock_service import OverstockService

router = APIRouter(prefix="/overstock", tags=["overstock"], dependencies=[Depends(verify_internal_token)])


@router.post("/detect", response_model=OverstockResponse)
def detect_overstock(request: OverstockRequest, db: Session = Depends(get_db)):
    service = OverstockService(db)
    return service.detect(product_id=request.product_id, store_id=request.store_id)