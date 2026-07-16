"""M8 — POST /api/v1/supplier/reliability"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.supplier import SupplierReliabilityRequest, SupplierReliabilityResponse
from app.services.supplier_service import SupplierService

router = APIRouter(prefix="/supplier", tags=["supplier"], dependencies=[Depends(verify_internal_token)])


@router.post("/reliability", response_model=SupplierReliabilityResponse)
def analyze_supplier_reliability(request: SupplierReliabilityRequest, db: Session = Depends(get_db)):
    service = SupplierService(db)
    return service.analyze_reliability(supplier_id=request.supplier_id)