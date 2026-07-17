"""Load classification thresholds and config from JSON files."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classification_thresholds.json"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classification_config.json"


@dataclass
class Thresholds:
    """Category-aware velocity thresholds (in units of average_daily_sales)."""
    fast: float
    medium: float
    slow: float


@dataclass
class Config:
    """Classification configuration constants."""
    min_days_with_sales_for_classification: int
    dead_stock_no_sale_days: int


def load_classification_thresholds(path: str | Path | None = None) -> dict[str, Thresholds]:
    """Load classification_thresholds.json into a category → Thresholds dict.

    Returns a dict like {"default": Thresholds(fast=10, medium=3, slow=0.5), ...}.
    """
    path = Path(path) if path else DEFAULT_THRESHOLDS_PATH

    if not path.exists():
        raise FileNotFoundError(f"Thresholds file not found at {path}")

    with open(path) as f:
        raw = json.load(f)

    thresholds: dict[str, Thresholds] = {}
    for category, values in raw.items():
        thresholds[category] = Thresholds(
            fast=values["fast"],
            medium=values["medium"],
            slow=values["slow"],
        )

    logger.info("Loaded %d category thresholds from %s", len(thresholds), path)
    return thresholds


def load_classification_config(path: str | Path | None = None) -> Config:
    """Load classification_config.json into a Config dataclass."""
    path = Path(path) if path else DEFAULT_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Config file not found at {path}")

    with open(path) as f:
        raw = json.load(f)

    config = Config(
        min_days_with_sales_for_classification=raw["min_days_with_sales_for_classification"],
        dead_stock_no_sale_days=raw["dead_stock_no_sale_days"],
    )

    logger.info("Loaded classification config from %s", path)
    return config