"""Load M1 consumption output and extract only the fields M5 needs.

This is the boundary where M1's unused fields (moving_average_*, volatility,
classification block, etc.) are stripped. Only ConsumptionMetric fields
cross into the classification service.
"""

import json
import logging
from pathlib import Path

from app.schemas.classification import ConsumptionMetric

logger = logging.getLogger(__name__)

DEFAULT_M1_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "module1_output.json"


def load_module1_metrics(path: str | Path | None = None) -> list[ConsumptionMetric]:
    """Read M1 output and return a list of ConsumptionMetric.

    Only the fields M5 needs are extracted — everything else is discarded.
    """
    path = Path(path) if path else DEFAULT_M1_PATH

    if not path.exists():
        raise FileNotFoundError(f"M1 output not found at {path}")

    with open(path) as f:
        raw = json.load(f)

    profiles = raw.get("profiles", [])
    metrics: list[ConsumptionMetric] = []

    for p in profiles:
        m = p.get("metrics", {})
        period = p.get("analysis_period", {})

        metric = ConsumptionMetric(
            product_id=p["product_id"],
            store_id=p["store_id"],
            average_daily_sales=m.get("average_daily_sales", 0.0),
            days_with_sales=m.get("days_with_sales", 0),
            last_sale_date=m.get("last_sale_date"),
            trend=m.get("trend"),
            analysis_period_end=period.get("end"),
        )
        metrics.append(metric)

    logger.info("Loaded %d consumption metrics from %s", len(metrics), path)
    return metrics