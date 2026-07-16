"""M9 — POST /api/v1/transfer/recommend"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.transfer import TransferRequest, TransferResponse
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/transfer", tags=["transfer"], dependencies=[Depends(verify_internal_token)])


@router.post("/recommend", response_model=TransferResponse)
def recommend_transfer(request: TransferRequest, db: Session = Depends(get_db)):
    service = TransferService(db)
    return service.recommend(
        product_id=request.product_id,
        from_store_id=request.from_store_id,
        to_store_id=request.to_store_id,
    )