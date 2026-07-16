"""M3 — POST /api/v1/reorder/recommend"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.reorder import ReorderRequest, ReorderResponse
from app.services.reorder_service import ReorderService

router = APIRouter(prefix="/reorder", tags=["reorder"], dependencies=[Depends(verify_internal_token)])


@router.post("/recommend", response_model=ReorderResponse)
def recommend_reorder(request: ReorderRequest, db: Session = Depends(get_db)):
    service = ReorderService(db)
    return service.recommend(product_id=request.product_id, store_id=request.store_id)