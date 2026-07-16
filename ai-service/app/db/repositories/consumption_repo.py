"""Consumption repository — query layer for ConsumptionProfile."""

from uuid import UUID
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.consumption_profile import ConsumptionProfile


class ConsumptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_product_store(
        self, product_id: UUID, store_id: UUID, start_date: date, end_date: date
    ) -> list[ConsumptionProfile]:
        stmt = (
            select(ConsumptionProfile)
            .where(
                ConsumptionProfile.product_id == product_id,
                ConsumptionProfile.store_id == store_id,
                ConsumptionProfile.date >= start_date,
                ConsumptionProfile.date <= end_date,
            )
            .order_by(ConsumptionProfile.date)
        )
        return list(self.db.execute(stmt).scalars().all())

    def save(self, profile: ConsumptionProfile) -> ConsumptionProfile:
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile