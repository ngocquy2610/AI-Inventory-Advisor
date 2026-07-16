"""Forecast repository."""

from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.forecast import Forecast


class ForecastRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_product_store(self, product_id: UUID, store_id: UUID) -> list[Forecast]:
        stmt = (
            select(Forecast)
            .where(Forecast.product_id == product_id, Forecast.store_id == store_id)
            .order_by(Forecast.forecast_date)
        )
        return list(self.db.execute(stmt).scalars().all())

    def save(self, forecast: Forecast) -> Forecast:
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def save_all(self, forecasts: list[Forecast]) -> list[Forecast]:
        self.db.add_all(forecasts)
        self.db.commit()
        for f in forecasts:
            self.db.refresh(f)
        return forecasts