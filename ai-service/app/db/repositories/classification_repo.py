"""Classification repository."""

from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.product_classification import ProductClassification


class ClassificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_product_store(self, product_id: UUID, store_id: UUID) -> ProductClassification | None:
        stmt = select(ProductClassification).where(
            ProductClassification.product_id == product_id,
            ProductClassification.store_id == store_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self) -> list[ProductClassification]:
        stmt = select(ProductClassification)
        return list(self.db.execute(stmt).scalars().all())

    def save(self, classification: ProductClassification) -> ProductClassification:
        self.db.add(classification)
        self.db.commit()
        self.db.refresh(classification)
        return classification