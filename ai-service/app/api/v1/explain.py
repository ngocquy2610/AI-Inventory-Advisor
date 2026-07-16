"""M7 — POST /api/v1/explain"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.services.explain_service import ExplainService

router = APIRouter(prefix="/explain", tags=["explain"], dependencies=[Depends(verify_internal_token)])


@router.post("", response_model=ExplainResponse)
def explain_recommendation(request: ExplainRequest, db: Session = Depends(get_db)):
    service = ExplainService(db)
    return service.explain(explainable_type=request.explainable_type, explainable_id=request.explainable_id)