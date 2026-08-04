"""M2 — POST /api/v1/forecast"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"], dependencies=[Depends(verify_internal_token)])


@router.post("", response_model=ForecastResponse)
def create_forecast(request: ForecastRequest, db: Session = Depends(get_db)):
    service = ForecastService(db)
    return service.forecast(
        product_id=request.product_id,
        store_id=request.store_id,
        horizon_days=request.horizon_days,
        geolocate=request.geolocate,
        localtime=request.localtime,
    )
