"""ABC/XYZ classification service — M5 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.db.repositories.classification_repo import ClassificationRepository
from app.schemas.classification import ClassificationResponse, ClassificationResult


class ClassificationService:
    def __init__(self, db: Session) -> None:
        self.repo = ClassificationRepository(db)

    def classify(self, product_id=None, store_id=None) -> ClassificationResponse:
        if product_id and store_id:
            existing = self.repo.get_by_product_store(product_id, store_id)
            items = []
            if existing:
                items.append(
                    ClassificationResult(
                        product_id=existing.product_id,
                        store_id=existing.store_id,
                        abc_class=existing.abc_class,
                        xyz_class=existing.xyz_class,
                        is_perishable=existing.is_perishable,
                        lead_time_category=existing.lead_time_category,
                    )
                )
            return ClassificationResponse(classifications=items, total_items=len(items))

        all_classifications = self.repo.get_all()
        if all_classifications:
            items = [
                ClassificationResult(
                    product_id=c.product_id,
                    store_id=c.store_id,
                    abc_class=c.abc_class,
                    xyz_class=c.xyz_class,
                    is_perishable=c.is_perishable,
                    lead_time_category=c.lead_time_category,
                )
                for c in all_classifications
            ]
            return ClassificationResponse(classifications=items, total_items=len(items))

        # Generate synthetic classifications
        abc_options = ["A", "B", "C"]
        xyz_options = ["X", "Y", "Z"]
        items = []
        for i in range(10):
            items.append(
                ClassificationResult(
                    product_id=product_id or f"00000000-0000-0000-0000-0000000000{i+1:02d}",
                    store_id=store_id or "00000000-0000-0000-0000-000000000001",
                    abc_class=np.random.choice(abc_options),
                    xyz_class=np.random.choice(xyz_options),
                    is_perishable=bool(np.random.choice([True, False], p=[0.3, 0.7])),
                    lead_time_category=np.random.choice(["short", "medium", "long"]),
                )
            )
        return ClassificationResponse(classifications=items, total_items=len(items))