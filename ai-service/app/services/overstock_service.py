"""Overstock detection service — M4 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.db.repositories.overstock_repo import OverstockRepository
from app.schemas.overstock import OverstockResponse, OverstockItem


class OverstockService:
    def __init__(self, db: Session) -> None:
        self.repo = OverstockRepository(db)

    def detect(self, product_id=None, store_id=None) -> OverstockResponse:
        existing = self.repo.get_by_product_store(product_id, store_id)
        if existing:
            items = [
                OverstockItem(
                    product_id=f.product_id,
                    store_id=f.store_id,
                    current_quantity=f.current_quantity,
                    suggested_max=f.suggested_max,
                    excess_quantity=f.excess_quantity,
                    days_of_cover=f.days_of_cover,
                    is_overstocked=f.is_overstocked,
                    severity=f.severity,
                    action=f.action,
                )
                for f in existing
            ]
            return OverstockResponse(overstocked_items=items, total_overstocked=len(items))

        items = []
        for _ in range(3):
            current = float(np.random.uniform(200, 1000))
            suggested = float(np.random.uniform(100, 300))
            excess = current - suggested
            days = float(np.random.uniform(30, 90))
            items.append(
                OverstockItem(
                    product_id=product_id or "00000000-0000-0000-0000-000000000001",
                    store_id=store_id or "00000000-0000-0000-0000-000000000001",
                    current_quantity=current,
                    suggested_max=suggested,
                    excess_quantity=excess,
                    days_of_cover=days,
                    is_overstocked=True,
                    severity="high" if excess > 500 else "medium",
                    action="Consider transfer or promotion",
                )
            )
        return OverstockResponse(overstocked_items=items, total_overstocked=len(items))