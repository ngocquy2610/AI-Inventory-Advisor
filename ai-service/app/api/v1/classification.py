"""M5 — POST /api/v1/classify"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.classification import ClassificationRequest, ClassificationResponse
from app.services.classification_service import ClassificationService

router = APIRouter(prefix="/classify", tags=["classification"], dependencies=[Depends(verify_internal_token)])


@router.post("", response_model=ClassificationResponse)
def classify_products(request: ClassificationRequest, db: Session = Depends(get_db)):
    service = ClassificationService(db)
    return service.classify(product_id=request.product_id, store_id=request.store_id)