"""Nightly batch: M2 (Forecast) + M5 (Classification — velocity tiers)."""

import json
import logging
from pathlib import Path

from app.db.session import SessionLocal
from app.services.forecast_service import ForecastService
from app.services.classification_service import (
    classify_batch,
    load_previous_tiers_from_file,
)
from app.data_access.module1_loader import load_module1_metrics
from app.data_access.product_lookup import load_product_categories
from app.data_access.thresholds_loader import (
    load_classification_thresholds,
    load_classification_config,
)

logger = logging.getLogger(__name__)

M5_OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "module5_output.json"


def run_analysis() -> None:
    """Run M2 and M5 batch analyses."""
    logger.info("Starting analysis batch (M2 + M5)...")

    # ── M2: Demand forecasts (existing) ──────────────────────────
    db = SessionLocal()
    try:
        forecast_svc = ForecastService(db)

        logger.info("Running demand forecasts...")
        # In production, iterate over all product-store combinations

        db.commit()
        logger.info("M2 forecasts completed.")
    except Exception as e:
        db.rollback()
        logger.error("M2 batch failed: %s", e)
        raise
    finally:
        db.close()

    # ── M5: Velocity classification (file-based, no DB dependency) ──
    logger.info("Running M5 velocity classification...")
    try:
        # Load M1 output
        metrics = load_module1_metrics()
        logger.info("  Loaded %d consumption metrics from M1", len(metrics))

        # Load product categories from M1 data (product IDs from M1 output,
        # category from M1 input). The old products.json stub is deleted
        # automatically after a successful load.
        category_map = load_product_categories()
        logger.info("  Loaded %d product categories from M1 data", len(category_map))

        # Load thresholds & config
        thresholds = load_classification_thresholds()
        config = load_classification_config()

        # Load previous tiers for tier_changed detection
        previous_tiers = load_previous_tiers_from_file(str(M5_OUTPUT_PATH))

        # Run classification
        output = classify_batch(
            metrics=metrics,
            category_map=category_map,
            thresholds=thresholds,
            config=config,
            previous_tiers=previous_tiers,
        )

        # Write output for downstream modules (M3, M4, M10, M11)
        M5_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(M5_OUTPUT_PATH, "w") as f:
            json.dump(output.model_dump(), f, indent=2, default=str)

        logger.info(
            "M5 classification completed: %d classified, %d insufficient_data",
            output.meta.total_classified,
            output.meta.total_insufficient_data,
        )

        # TODO: Persist to product_classifications table once Rails↔AI wiring is ready
        # db = SessionLocal()
        # try:
        #     repo = ClassificationRepository(db)
        #     for c in output.classifications:
        #         repo.upsert(product_id=c.product_id, store_id=c.store_id, tier=c.tier, computed_at=c.computed_at)
        #     db.commit()
        # finally:
        #     db.close()

        logger.info("M5 velocity classification completed successfully.")
    except Exception as e:
        logger.error("M5 batch failed: %s", e)
        raise


if __name__ == "__main__":
    run_analysis()
