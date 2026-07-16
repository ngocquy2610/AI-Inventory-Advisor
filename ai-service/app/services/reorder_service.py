"""Reorder recommendation service — M3 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.db.repositories.reorder_repo import ReorderRepository
from app.schemas.reorder import ReorderResponse, ReorderItem


class ReorderService:
    def __init__(self, db: Session) -> None:
        self.repo = ReorderRepository(db)

    def recommend(self, product_id=None, store_id=None) -> ReorderResponse:
        existing = self.repo.get_by_product_store(product_id, store_id)
        if existing:
            items = [
                ReorderItem(
                    product_id=r.product_id,
                    store_id=r.store_id,
                    current_stock=r.current_stock,
                    recommended_quantity=r.recommended_quantity,
                    reorder_point=r.reorder_point,
                    economic_order_quantity=r.economic_order_quantity,
                    priority=r.priority,
                    reason=r.reason,
                )
                for r in existing
            ]
            return ReorderResponse(recommendations=items, total_items=len(items))

        # Generate synthetic recommendations
        items = []
        for _ in range(5):
            current = float(np.random.uniform(0, 200))
            reorder_point = float(np.random.uniform(50, 150))
            if current < reorder_point:
                items.append(
                    ReorderItem(
                        product_id=product_id or "00000000-0000-0000-0000-000000000001",
                        store_id=store_id or "00000000-0000-0000-0000-000000000001",
                        current_stock=current,
                        recommended_quantity=float(np.random.uniform(100, 500)),
                        reorder_point=reorder_point,
                        economic_order_quantity=float(np.random.uniform(200, 400)),
                        priority="high" if current < reorder_point * 0.5 else "medium",
                        reason="Stock below reorder point",
                    )
                )
        return ReorderResponse(recommendations=items, total_items=len(items))