"""Simulation schemas."""

from uuid import UUID

from pydantic import BaseModel


class SimulationRequest(BaseModel):
    product_id: UUID
    store_id: UUID
    scenario_name: str = "baseline"
    parameters: dict = {}


class SimulationResult(BaseModel):
    scenario_name: str
    expected_demand: float
    expected_stockout_probability: float
    expected_overstock_probability: float
    optimal_stock_level: float | None = None
    total_cost_estimate: float | None = None


class SimulationResponse(BaseModel):
    product_id: UUID
    store_id: UUID
    results: list[SimulationResult]
    iterations: int