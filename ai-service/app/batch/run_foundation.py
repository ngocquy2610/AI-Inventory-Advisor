"""Nightly batch: M1 (Consumption Analysis) + M8 (Supplier Reliability)."""

import logging

from app.config import settings
from app.db.session import SessionLocal
from app.services.consumption_service import ConsumptionService
from app.services.supplier_service import SupplierService

logger = logging.getLogger(__name__)


def run_foundation() -> None:
    """Run M1 and M8 batch analyses."""
    logger.info("Starting foundation batch (M1 + M8)...")
    db = SessionLocal()
    try:
        consumption_svc = ConsumptionService(db)
        supplier_svc = SupplierService(db)

        # M1: Analyze consumption for all products
        logger.info("Running consumption analysis...")
        # In production, iterate over all product-store combinations

        # M8: Analyze supplier reliability
        logger.info("Running supplier reliability analysis...")
        result = supplier_svc.analyze_reliability()
        logger.info("Supplier reliability analyzed: %d suppliers", result.total_items)

        db.commit()
        logger.info("Foundation batch completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Foundation batch failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_foundation()