"""Overstock flag repository."""

from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.overstock_flag import OverstockFlag


class OverstockRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_product_store(self, product_id: UUID | None = None, store_id: UUID | None = None) -> list[OverstockFlag]:
        stmt = select(OverstockFlag)
        if product_id:
            stmt = stmt.where(OverstockFlag.product_id == product_id)
        if store_id:
            stmt = stmt.where(OverstockFlag.store_id == store_id)
        return list(self.db.execute(stmt).scalars().all())

    def save(self, flag: OverstockFlag) -> OverstockFlag:
        self.db.add(flag)
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def save_all(self, flags: list[OverstockFlag]) -> list[OverstockFlag]:
        self.db.add_all(flags)
        self.db.commit()
        for f in flags:
            self.db.refresh(f)
        return flags