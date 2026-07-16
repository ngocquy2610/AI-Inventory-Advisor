"""Reorder recommendation repository."""

from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.reorder_recommendation import ReorderRecommendation


class ReorderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_product_store(self, product_id: UUID | None = None, store_id: UUID | None = None) -> list[ReorderRecommendation]:
        stmt = select(ReorderRecommendation)
        if product_id:
            stmt = stmt.where(ReorderRecommendation.product_id == product_id)
        if store_id:
            stmt = stmt.where(ReorderRecommendation.store_id == store_id)
        stmt = stmt.order_by(ReorderRecommendation.priority)
        return list(self.db.execute(stmt).scalars().all())

    def save(self, rec: ReorderRecommendation) -> ReorderRecommendation:
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def save_all(self, recs: list[ReorderRecommendation]) -> list[ReorderRecommendation]:
        self.db.add_all(recs)
        self.db.commit()
        for r in recs:
            self.db.refresh(r)
        return recs