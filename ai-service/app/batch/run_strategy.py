"""Nightly batch: M12 (Strategy) + M7 (Explanation)."""

import logging

from app.db.session import SessionLocal
from app.services.strategy_service import StrategyService
from app.services.explain_service import ExplainService

logger = logging.getLogger(__name__)


def run_strategy() -> None:
    """Run M12 and M7 batch analyses."""
    logger.info("Starting strategy batch (M12 + M7)...")
    db = SessionLocal()
    try:
        strategy_svc = StrategyService(db)
        explain_svc = ExplainService(db)

        # M12: Generate strategies
        logger.info("Running strategy generation...")
        # In production, iterate over all stores

        # M7: Generate explanations
        logger.info("Running explanation generation...")
        # In production, iterate over all recommendations needing explanations

        db.commit()
        logger.info("Strategy batch completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Strategy batch failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_strategy()