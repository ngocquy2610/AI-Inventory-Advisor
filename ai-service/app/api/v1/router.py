"""Aggregates all v1 routers."""

from fastapi import APIRouter

from app.api.v1.consumption import router as consumption_router
from app.api.v1.forecast import router as forecast_router
from app.api.v1.reorder import router as reorder_router
from app.api.v1.overstock import router as overstock_router
from app.api.v1.classification import router as classification_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.explain import router as explain_router
from app.api.v1.supplier import router as supplier_router
from app.api.v1.transfer import router as transfer_router
from app.api.v1.chat import router as chat_router
from app.api.v1.report import router as report_router
from app.api.v1.strategy import router as strategy_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(consumption_router)
api_v1_router.include_router(forecast_router)
api_v1_router.include_router(reorder_router)
api_v1_router.include_router(overstock_router)
api_v1_router.include_router(classification_router)
api_v1_router.include_router(simulation_router)
api_v1_router.include_router(explain_router)
api_v1_router.include_router(supplier_router)
api_v1_router.include_router(transfer_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(report_router)
api_v1_router.include_router(strategy_router)