"""Transfer recommendation service — M9 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.schemas.transfer import TransferResponse, TransferItem


class TransferService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def recommend(self, product_id=None, from_store_id=None, to_store_id=None) -> TransferResponse:
        # Generate synthetic transfer recommendations
        items = []
        for i in range(3):
            items.append(
                TransferItem(
                    product_id=product_id or f"00000000-0000-0000-0000-0000000000{i+1:02d}",
                    product_name=f"Product {i+1}",
                    from_store_id=from_store_id or "00000000-0000-0000-0000-000000000001",
                    to_store_id=to_store_id or "00000000-0000-0000-0000-000000000002",
                    quantity=float(np.random.uniform(10, 100)),
                    reason="Excess stock at source store, low stock at destination",
                    priority=np.random.choice(["high", "medium", "low"]),
                )
            )
        return TransferResponse(recommendations=items, total_items=len(items))