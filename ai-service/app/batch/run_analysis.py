"""Nightly batch: M2 (Forecast) + M5 (Classification)."""

import logging

from app.db.session import SessionLocal
from app.services.forecast_service import ForecastService
from app.services.classification_service import ClassificationService

logger = logging.getLogger(__name__)


def run_analysis() -> None:
    """Run M2 and M5 batch analyses."""
    logger.info("Starting analysis batch (M2 + M5)...")
    db = SessionLocal()
    try:
        forecast_svc = ForecastService(db)
        classification_svc = ClassificationService(db)

        # M2: Generate forecasts
        logger.info("Running demand forecasts...")
        # In production, iterate over all product-store combinations

        # M5: Run classification
        logger.info("Running product classification...")
        result = classification_svc.classify()
        logger.info("Classification completed: %d items", result.total_items)

        db.commit()
        logger.info("Analysis batch completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Analysis batch failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_analysis()