"""M5 — Velocity tier classification service.

Pure functions — no I/O inside the classify() function itself.
All data loading (M1 metrics, product categories, thresholds) is
injected from outside so classify() is testable in isolation.

──────────────────────────────────────────────────────────────────────
Open decisions made during this build (see also services/README.md):

1. M1's embedded classification block (consumption_speed, score,
   status) is explicitly ignored by M5. Tiers are computed
   independently from raw metrics to avoid two modules disagreeing
   on velocity. A follow-up should decide whether to strip
   classification out of M1's output entirely.

2. Category is derived from M1 data files (module1_output.json
   product IDs × module1_input.json product catalog). When the
   Rails BE integration is wired up, this will come directly in
   the API payload. The swap is a one-line change in the
   orchestration layer — the classify() pure function already
   accepts category as a parameter.
──────────────────────────────────────────────────────────────────────
"""

import logging
from datetime import datetime, date, timezone

from app.schemas.classification import (
    ConsumptionMetric,
    ClassificationResult,
    ClassificationBatchOutput,
    ClassificationBatchMeta,
)
from app.data_access.thresholds_loader import Thresholds, Config

logger = logging.getLogger(__name__)


def classify(
    metric: ConsumptionMetric,
    category: str,
    thresholds: dict[str, Thresholds],
    config: Config,
    previous_tier: str | None,
    computed_at: datetime | None = None,
) -> ClassificationResult:
    """Classify a single product-store into a velocity tier.

    Logic order (strict):
    1. Compute days_since_last_sale from analysis_period_end - last_sale_date.
    2. If days_with_sales < min_days_with_sales_for_classification → insufficient_data.
    3. If days_since_last_sale >= dead_stock_no_sale_days → tier = "dead" (override).
    4. Else look up thresholds.get(category, thresholds["default"]), apply cutoffs.
    5. Set tier_changed = (previous_tier is not None and previous_tier != tier).
    """
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)

    # Step 1: days since last sale
    days_since_last_sale = (metric.analysis_period_end - metric.last_sale_date).days

    # Step 2: insufficient data check
    if metric.days_with_sales < config.min_days_with_sales_for_classification:
        return ClassificationResult(
            product_id=metric.product_id,
            store_id=metric.store_id,
            category=category,
            tier=None,
            previous_tier=previous_tier,
            tier_changed=False,
            insufficient_data=True,
            days_since_last_sale=days_since_last_sale,
            average_daily_sales=metric.average_daily_sales,
            computed_at=computed_at,
        )

    # Step 3: dead-stock recency override
    if days_since_last_sale >= config.dead_stock_no_sale_days:
        tier = "dead"
    else:
        # Step 4: threshold-based classification
        t = thresholds.get(category, thresholds["default"])
        ads = metric.average_daily_sales

        if ads >= t.fast:
            tier = "fast"
        elif ads >= t.medium:
            tier = "medium"
        elif ads >= t.slow:
            tier = "slow"
        else:
            tier = "dead"

    # Step 5: detect tier change
    tier_changed = previous_tier is not None and previous_tier != tier

    return ClassificationResult(
        product_id=metric.product_id,
        store_id=metric.store_id,
        category=category,
        tier=tier,
        previous_tier=previous_tier,
        tier_changed=tier_changed,
        insufficient_data=False,
        days_since_last_sale=days_since_last_sale,
        average_daily_sales=metric.average_daily_sales,
        computed_at=computed_at,
    )


def load_previous_tiers_from_file(path: str) -> dict[tuple[str, str], str]:
    """Read last run's module5_output.json and return (product_id, store_id) → tier map.

    Used for local dev to compute tier_changed. In production this reads
    the most recent row per product/store from product_classifications instead.
    """
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        logger.info("No previous classification output found at %s — all tiers treated as new", path)
        return {}

    with open(p) as f:
        raw = json.load(f)

    previous: dict[tuple[str, str], str] = {}
    for c in raw.get("classifications", []):
        key = (c["product_id"], c["store_id"])
        if c.get("tier") is not None:
            previous[key] = c["tier"]

    logger.info("Loaded %d previous tiers from %s", len(previous), path)
    return previous


def classify_batch(
    metrics: list[ConsumptionMetric],
    category_map: dict[str, str],
    thresholds: dict[str, Thresholds],
    config: Config,
    previous_tiers: dict[tuple[str, str], str] | None = None,
) -> ClassificationBatchOutput:
    """Classify a batch of M1 consumption metrics into velocity tiers.

    Parameters
    ----------
    metrics : list[ConsumptionMetric]
        Parsed from M1 output (only fields M5 needs).
    category_map : dict[str, str]
        product_id → category mapping.
    thresholds : dict[str, Thresholds]
        Category-aware velocity thresholds.
    config : Config
        Classification configuration (min days, dead-stock window, etc.).
    previous_tiers : dict[tuple[str, str], str] | None
        (product_id, store_id) → previous tier for tier_changed detection.

    Returns
    -------
    ClassificationBatchOutput
        Ready to serialize to module5_output.json.
    """
    if previous_tiers is None:
        previous_tiers = {}

    computed_at = datetime.now(timezone.utc)
    results: list[ClassificationResult] = []

    for metric in metrics:
        category = category_map.get(metric.product_id, "default")
        prev = previous_tiers.get((metric.product_id, metric.store_id))

        result = classify(
            metric=metric,
            category=category,
            thresholds=thresholds,
            config=config,
            previous_tier=prev,
            computed_at=computed_at,
        )
        results.append(result)

    total_classified = sum(1 for r in results if not r.insufficient_data and r.tier is not None)
    total_insufficient_data = sum(1 for r in results if r.insufficient_data)

    meta = ClassificationBatchMeta(
        source_file="data/module1_output.json",
        thresholds_version="2026-07-17",
        total_classified=total_classified,
        total_insufficient_data=total_insufficient_data,
    )

    return ClassificationBatchOutput(classifications=results, meta=meta)