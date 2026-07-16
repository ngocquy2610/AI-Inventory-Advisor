"""Consumption analysis service — M1 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.db.repositories.consumption_repo import ConsumptionRepository
from app.schemas.consumption import ConsumptionAnalysisResponse, ConsumptionMetric


class ConsumptionService:
    def __init__(self, db: Session) -> None:
        self.repo = ConsumptionRepository(db)

    def analyze(self, product_id, store_id, start_date, end_date) -> ConsumptionAnalysisResponse:
        profiles = self.repo.get_by_product_store(product_id, store_id, start_date, end_date)
        if not profiles:
            return ConsumptionAnalysisResponse(
                product_id=product_id,
                store_id=store_id,
                metrics=[],
                total_consumption=0.0,
                average_daily_consumption=0.0,
            )

        quantities = [p.quantity_sold for p in profiles]
        total = float(np.sum(quantities))
        avg = float(np.mean(quantities))
        trend = "increasing" if len(quantities) > 1 and quantities[-1] > quantities[0] else "decreasing" if len(quantities) > 1 and quantities[-1] < quantities[0] else "stable"

        metrics = [
            ConsumptionMetric(
                period=p.date.isoformat(),
                total_sold=p.quantity_sold,
                average_daily=p.quantity_sold,
                seasonality_factor=p.seasonality_factor,
                trend=p.trend,
            )
            for p in profiles
        ]

        return ConsumptionAnalysisResponse(
            product_id=product_id,
            store_id=store_id,
            metrics=metrics,
            total_consumption=total,
            average_daily_consumption=avg,
            trend_direction=trend,
        )