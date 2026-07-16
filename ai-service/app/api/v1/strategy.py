"""M12 — POST /api/v1/strategy/generate"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.strategy import StrategyRequest, StrategyResponse
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategy", tags=["strategy"], dependencies=[Depends(verify_internal_token)])


@router.post("/generate", response_model=StrategyResponse)
def generate_strategy(request: StrategyRequest, db: Session = Depends(get_db)):
    service = StrategyService(db)
    return service.generate(store_id=request.store_id, strategy_type=request.strategy_type)