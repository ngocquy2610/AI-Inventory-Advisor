"""Orchestrates the full nightly chain in order."""

import logging

from app.batch.run_foundation import run_foundation
from app.batch.run_analysis import run_analysis
from app.batch.run_decision import run_decision
from app.batch.run_strategy import run_strategy

logger = logging.getLogger(__name__)


def run_all() -> None:
    """Run all nightly batch jobs in the correct order."""
    logger.info("=" * 50)
    logger.info("Starting full nightly batch pipeline")
    logger.info("=" * 50)

    # Step 1: Foundation (M1 + M8)
    logger.info("Step 1/4: Foundation")
    run_foundation()

    # Step 2: Analysis (M2 + M5)
    logger.info("Step 2/4: Analysis")
    run_analysis()

    # Step 3: Decision (M3 + M4 + M9)
    logger.info("Step 3/4: Decision")
    run_decision()

    # Step 4: Strategy (M12 + M7)
    logger.info("Step 4/4: Strategy")
    run_strategy()

    logger.info("=" * 50)
    logger.info("Full nightly batch pipeline completed")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_all()