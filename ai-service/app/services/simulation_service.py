"""Simulation service — M6 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.schemas.simulation import SimulationResponse, SimulationResult


class SimulationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def simulate(self, product_id, store_id, scenario_name="baseline", parameters=None) -> SimulationResponse:
        params = parameters or {}
        base_demand = params.get("base_demand", 100)
        variability = params.get("variability", 0.2)

        iterations = 1000
        results = []

        # Run Monte Carlo simulation
        demands = np.random.normal(base_demand, base_demand * variability, iterations)
        stockout = float(np.mean(demands > base_demand * 1.3))
        overstock = float(np.mean(demands < base_demand * 0.7))

        results.append(
            SimulationResult(
                scenario_name=scenario_name,
                expected_demand=float(np.mean(demands)),
                expected_stockout_probability=stockout,
                expected_overstock_probability=overstock,
                optimal_stock_level=float(np.percentile(demands, 85)),
                total_cost_estimate=float(np.mean(demands) * 10),
            )
        )

        return SimulationResponse(
            product_id=product_id,
            store_id=store_id,
            results=results,
            iterations=iterations,
        )