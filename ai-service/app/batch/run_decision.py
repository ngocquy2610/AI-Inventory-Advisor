"""Nightly batch: M3 (Reorder) + M4 (Overstock) + M9 (Transfer)."""

import logging

from app.db.session import SessionLocal
from app.services.reorder_service import ReorderService
from app.services.overstock_service import OverstockService
from app.services.transfer_service import TransferService

logger = logging.getLogger(__name__)


def run_decision() -> None:
    """Run M3, M4, and M9 batch analyses."""
    logger.info("Starting decision batch (M3 + M4 + M9)...")
    db = SessionLocal()
    try:
        reorder_svc = ReorderService(db)
        overstock_svc = OverstockService(db)
        transfer_svc = TransferService(db)

        # M3: Reorder recommendations
        logger.info("Running reorder recommendations...")
        reorder_result = reorder_svc.recommend()
        logger.info("Reorder recommendations: %d items", reorder_result.total_items)

        # M4: Overstock detection
        logger.info("Running overstock detection...")
        overstock_result = overstock_svc.detect()
        logger.info("Overstock detected: %d items", overstock_result.total_overstocked)

        # M9: Transfer recommendations
        logger.info("Running transfer recommendations...")
        transfer_result = transfer_svc.recommend()
        logger.info("Transfer recommendations: %d items", transfer_result.total_items)

        db.commit()
        logger.info("Decision batch completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Decision batch failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_decision()