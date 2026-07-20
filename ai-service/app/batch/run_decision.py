"""Nightly batch: M3 (Reorder) + M4 (Overstock) + M9 (Transfer).

M3 and M9 still use DB-based services (legacy).
M4 now uses the file-based batch pipeline (run_overstock_batch + write).
"""

import logging
from pathlib import Path

from app.db.session import SessionLocal
from app.services.reorder_service import ReorderService
from app.services.transfer_service import TransferService
from app.services.overstock_service import (
    run_overstock_batch,
    write_overstock_output,
)

logger = logging.getLogger(__name__)


def run_decision() -> None:
    """Run M3, M4, and M9 batch analyses.

    Order:
      1. M3 — Reorder recommendations (DB-based)
      2. M4 — Overstock detection (file-based, no DB dependency)
      3. M9 — Transfer recommendations (DB-based)
    """
    logger.info("Starting decision batch (M3 + M4 + M9)...")

    # ── M3: Reorder recommendations ──────────────────────────────
    db = SessionLocal()
    try:
        reorder_svc = ReorderService(db)
        logger.info("Running reorder recommendations...")
        reorder_result = reorder_svc.recommend()
        logger.info("Reorder recommendations: %d items", reorder_result.total_items)

        # M9: Transfer recommendations
        transfer_svc = TransferService(db)
        logger.info("Running transfer recommendations...")
        transfer_result = transfer_svc.recommend()
        logger.info("Transfer recommendations: %d items", transfer_result.total_items)

        db.commit()
        logger.info("M3 + M9 batch completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("M3/M9 batch failed: %s", e)
        raise
    finally:
        db.close()

    # ── M4: Overstock detection (file-based, no DB dependency) ───
    logger.info("Running M4 overstock detection...")
    try:
        output = run_overstock_batch()
        write_overstock_output(output)

        logger.info(
            "M4 overstock detection completed: %d evaluated, "
            "%d high, %d medium, %d dead (zero velocity), "
            "%d insufficient_data",
            output.meta.total_evaluated,
            output.meta.total_flagged_high,
            output.meta.total_flagged_medium,
            output.meta.total_dead_zero_velocity,
            output.meta.total_skipped_insufficient_data,
        )
    except Exception as e:
        logger.error("M4 batch failed: %s", e)
        raise

    logger.info("Decision batch (M3 + M4 + M9) completed successfully.")


if __name__ == "__main__":
    run_decision()