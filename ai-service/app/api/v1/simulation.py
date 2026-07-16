"""M6 — POST /api/v1/simulate"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulate", tags=["simulation"], dependencies=[Depends(verify_internal_token)])


@router.post("", response_model=SimulationResponse)
def run_simulation(request: SimulationRequest, db: Session = Depends(get_db)):
    service = SimulationService(db)
    return service.simulate(
        product_id=request.product_id,
        store_id=request.store_id,
        scenario_name=request.scenario_name,
        parameters=request.parameters,
    )