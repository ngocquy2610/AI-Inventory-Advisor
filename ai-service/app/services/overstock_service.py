"""M4 — Overstock detection service.

Pure functions for core calculation — no I/O.
Batch orchestration functions handle data loading and writing.

┌──────────────────────────────────────────────────────────────────────┐
│ Design decisions (see also services/README.md):                     │
│                                                                      │
│ 1. M4 does NOT re-derive current_stock or category from M1/M5.      │
│    Those come from module1_input.json (product_store_stock +        │
│    products), which is the raw/live data source.                     │
│                                                                      │
│ 2. current_stock == 0 rows are explicitly skipped (belongs to       │
│    M2/M3's stockout side).                                          │
│                                                                      │
│ 3. stock_data_stale: true still outputs the row (soft-flag).        │
│    Downstream modules discount confidence.                           │
│                                                                      │
│ 4. Category-specific threshold overrides are stubbed for v2.        │
│    V1 uses global RISK_THRESHOLDS for all categories.               │
│                                                                      │
│ 5. avg_daily_sales == 0 → days_of_supply = null, risk_level =       │
│    "dead_zero_velocity", suggested_action = "flash_sale". This is   │
│    treated as a separate case, not assigned a risk_level from the   │
│    normal threshold ladder.                                          │
└──────────────────────────────────────────────────────────────────────┘

Thresholds & rules are hardcoded as module-level constants for v1.
In a future version these could be loaded from a config file or DB
table (the app/config.py Settings class is environment-based, not
suited for business-rule thresholds).
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.schemas.overstock import (
    ConsumptionProfile,
    ProductStoreStock,
    Product,
    ClassificationRow,
    OverstockFlag,
    OverstockRunMeta,
    OverstockOutput,
)

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════
# Thresholds & rules (hardcoded for v1 — see design note above)
# ═════════════════════════════════════════════════════════════════════

OVERSTOCK_THRESHOLD_DAYS = 90

RISK_THRESHOLDS: dict[str, float] = {
    "high": 180.0,
    "medium": 90.0,
}

CLEARANCE_ACTION_RULES: dict[str, str | None] = {
    "high": "flash_sale",
    "medium": "discount",
    "low": None,
}

STALE_STOCK_MAX_AGE = timedelta(days=2)

# Which M1 metric to use for days_of_supply calculation.
# Options: "average_daily_sales" or "moving_average_7"
VELOCITY_FIELD = "average_daily_sales"

# Category-specific threshold overrides (v2 stub — empty for v1).
CATEGORY_THRESHOLD_OVERRIDES: dict[str, dict[str, float]] = {}


# ── Default file paths (relative to project root) ────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_M1_OUTPUT_PATH = _PROJECT_ROOT / "data" / "module1_output.json"
DEFAULT_M1_INPUT_PATH = _PROJECT_ROOT / "data" / "module1_input.json"
DEFAULT_M5_OUTPUT_PATH = _PROJECT_ROOT / "data" / "module5_output.json"
DEFAULT_M4_OUTPUT_PATH = _PROJECT_ROOT / "data" / "module4_output.json"


# ═════════════════════════════════════════════════════════════════════
# Data loader functions
# ═════════════════════════════════════════════════════════════════════


def load_consumption_profiles(path: str | Path) -> dict[tuple[str, str], ConsumptionProfile]:
    """Load M1 consumption profiles keyed by (product_id, store_id)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"M1 output not found at {path}")

    with open(path) as f:
        raw = json.load(f)

    profiles: dict[tuple[str, str], ConsumptionProfile] = {}
    for p in raw.get("profiles", []):
        metrics = p.get("metrics", {})
        profile = ConsumptionProfile(
            product_id=p["product_id"],
            store_id=p["store_id"],
            average_daily_sales=metrics.get("average_daily_sales", 0.0),
            moving_average_7=metrics.get("moving_average_7"),
            trend=metrics.get("trend"),
        )
        key = (profile.product_id, profile.store_id)
        profiles[key] = profile

    logger.info("Loaded %d consumption profiles from %s", len(profiles), path)
    return profiles


def load_stock_and_catalog(
    path: str | Path,
) -> tuple[dict[tuple[str, str], ProductStoreStock], dict[str, str]]:
    """Load product_store_stock + product catalogue from module1_input.json.

    Returns
    -------
    stock_map : dict[(product_id, store_id), ProductStoreStock]
    category_map : dict[product_id, category]
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"M1 input not found at {path}")

    with open(path) as f:
        raw = json.load(f)

    # Load stock rows
    stock_map: dict[tuple[str, str], ProductStoreStock] = {}
    for s in raw.get("product_store_stock", []):
        stock_row = ProductStoreStock(
            product_id=s["product_id"],
            store_id=s["store_id"],
            current_stock=float(s.get("current_stock", 0)),
            updated_at=s["updated_at"],
        )
        key = (stock_row.product_id, stock_row.store_id)
        stock_map[key] = stock_row

    # Load product catalogue
    category_map: dict[str, str] = {}
    for prod in raw.get("products", []):
        category_map[prod["id"]] = prod.get("category", "default")

    logger.info(
        "Loaded %d stock rows and %d product categories from %s",
        len(stock_map),
        len(category_map),
        path,
    )
    return stock_map, category_map


def load_classifications(path: str | Path) -> dict[tuple[str, str], ClassificationRow]:
    """Load M5 classification output keyed by (product_id, store_id)."""
    path = Path(path)
    if not path.exists():
        logger.warning("M5 output not found at %s — all tiers treated as unknown", path)
        return {}

    with open(path) as f:
        raw = json.load(f)

    classifications: dict[tuple[str, str], ClassificationRow] = {}
    for c in raw.get("classifications", []):
        row = ClassificationRow(
            product_id=c["product_id"],
            store_id=c["store_id"],
            tier=c.get("tier"),
            insufficient_data=c.get("insufficient_data", False),
        )
        key = (row.product_id, row.store_id)
        classifications[key] = row

    logger.info("Loaded %d classifications from %s", len(classifications), path)
    return classifications


# ═════════════════════════════════════════════════════════════════════
# Pure calculation function
# ═════════════════════════════════════════════════════════════════════


def get_velocity_value(profile: ConsumptionProfile) -> float:
    """Extract the configured velocity value from a consumption profile.

    Uses VELOCITY_FIELD to pick between average_daily_sales and
    moving_average_7. Falls back to average_daily_sales if the
    configured field is None.
    """
    if VELOCITY_FIELD == "moving_average_7":
        return profile.moving_average_7 if profile.moving_average_7 is not None else profile.average_daily_sales
    return profile.average_daily_sales


def get_effective_thresholds(category: str) -> dict[str, float]:
    """Resolve thresholds for a category, falling back to global defaults.

    V2 stub: CATEGORY_THRESHOLD_OVERRIDES is empty in v1, so this
    always returns global RISK_THRESHOLDS. In v2, add overrides per
    category (e.g. electronics can sit longer than groceries before
    being flagged overstock).
    """
    override = CATEGORY_THRESHOLD_OVERRIDES.get(category)
    if override is not None:
        return override
    return RISK_THRESHOLDS


def calculate_overstock_flag(
    current_stock: float,
    avg_daily_sales: float,
    category: str,
    tier: str | None,
    updated_at: datetime,
    now: datetime | None = None,
) -> dict:
    """Core calculation — pure function, no I/O.

    Parameters
    ----------
    current_stock : float
        Current inventory quantity.
    avg_daily_sales : float
        Average daily sales velocity from M1.
    category : str
        Product category (for future category-aware thresholds).
    tier : str | None
        M5 velocity tier (None if insufficient_data).
    updated_at : datetime
        When the stock record was last updated.
    now : datetime | None
        Reference timestamp (defaults to UTC now).

    Returns
    -------
    dict with keys:
        days_of_supply : float | None
        risk_level : str
        suggested_action : str | None
        stock_data_stale : bool
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Case 1: Zero velocity → dead stock / zero velocity
    if avg_daily_sales == 0:
        return {
            "days_of_supply": None,
            "risk_level": "dead_zero_velocity",
            "suggested_action": "flash_sale",
            "stock_data_stale": (now - updated_at).days > STALE_STOCK_MAX_AGE.days,
        }

    # Case 2: Normal calculation
    days_of_supply = round(current_stock / avg_daily_sales, 1)

    thresholds = get_effective_thresholds(category)
    if days_of_supply >= thresholds["high"]:
        risk_level = "high"
    elif days_of_supply >= thresholds["medium"]:
        risk_level = "medium"
    else:
        risk_level = "low"

    suggested_action = CLEARANCE_ACTION_RULES[risk_level]
    stock_data_stale = (now - updated_at).days > STALE_STOCK_MAX_AGE.days

    return {
        "days_of_supply": days_of_supply,
        "risk_level": risk_level,
        "suggested_action": suggested_action,
        "stock_data_stale": stock_data_stale,
    }


# ═════════════════════════════════════════════════════════════════════
# Batch orchestration
# ═════════════════════════════════════════════════════════════════════


def run_overstock_batch(
    m1_output_path: str | Path | None = None,
    m1_input_path: str | Path | None = None,
    m5_output_path: str | Path | None = None,
) -> OverstockOutput:
    """Run the full M4 overstock detection batch.

    Loads all three input files, performs the join/calculation,
    and returns the output object ready for serialization.

    Parameters
    ----------
    m1_output_path : str | Path | None
        Path to module1_output.json.
    m1_input_path : str | Path | None
        Path to module1_input.json.
    m5_output_path : str | Path | None
        Path to module5_output.json.

    Returns
    -------
    OverstockOutput
        Ready to serialize to module4_output.json.
    """
    m1_out = Path(m1_output_path) if m1_output_path else DEFAULT_M1_OUTPUT_PATH
    m1_in = Path(m1_input_path) if m1_input_path else DEFAULT_M1_INPUT_PATH
    m5_out = Path(m5_output_path) if m5_output_path else DEFAULT_M5_OUTPUT_PATH

    # Load all data sources
    consumption_profiles = load_consumption_profiles(m1_out)
    stock_map, category_map = load_stock_and_catalog(m1_in)
    classifications = load_classifications(m5_out)

    computed_at = datetime.now(timezone.utc)

    flags: list[OverstockFlag] = []
    meta = OverstockRunMeta(computed_at=computed_at)

    # Iterate over every (product_id, store_id) in stock_map (the "live" table)
    for key, stock_row in stock_map.items():
        product_id, store_id = key

        # Skip zero-stock rows (belongs to M2/M3 stockout analysis)
        if stock_row.current_stock == 0:
            meta.total_skipped_zero_stock += 1
            continue

        # Look up consumption profile
        profile = consumption_profiles.get(key)
        if profile is None:
            logger.warning(
                "Missing consumption profile for %s / %s — skipping",
                product_id,
                store_id,
            )
            meta.total_skipped_missing_consumption += 1
            continue

        # Look up classification
        classification = classifications.get(key)
        tier: str | None = None
        insufficient_data: bool = False
        if classification:
            tier = classification.tier
            insufficient_data = classification.insufficient_data

        # Look up category
        category = category_map.get(product_id, "default")

        # Get velocity value from the configured field
        avg_daily_sales = get_velocity_value(profile)

        # Core calculation
        calc_result = calculate_overstock_flag(
            current_stock=stock_row.current_stock,
            avg_daily_sales=avg_daily_sales,
            category=category,
            tier=tier,
            updated_at=stock_row.updated_at,
            now=computed_at,
        )

        # Build the output flag
        flag = OverstockFlag(
            product_id=product_id,
            store_id=store_id,
            category=category,
            current_stock=stock_row.current_stock,
            average_daily_sales=avg_daily_sales,
            days_of_supply=calc_result["days_of_supply"],
            risk_level=calc_result["risk_level"],
            suggested_action=calc_result["suggested_action"],
            tier=tier,
            stock_data_stale=calc_result["stock_data_stale"],
            insufficient_data=insufficient_data,
            computed_at=computed_at,
        )
        flags.append(flag)

    # Compute meta counters
    meta.total_evaluated = len(flags)

    for f in flags:
        if f.risk_level == "high":
            meta.total_flagged_high += 1
        elif f.risk_level == "medium":
            meta.total_flagged_medium += 1
        elif f.risk_level == "dead_zero_velocity":
            meta.total_dead_zero_velocity += 1

        if f.insufficient_data:
            meta.total_skipped_insufficient_data += 1

    logger.info(
        "Overstock batch complete: %d evaluated, %d high, %d medium, "
        "%d dead (zero velocity), %d insufficient_data, "
        "%d missing consumption, %d zero stock skipped",
        meta.total_evaluated,
        meta.total_flagged_high,
        meta.total_flagged_medium,
        meta.total_dead_zero_velocity,
        meta.total_skipped_insufficient_data,
        meta.total_skipped_missing_consumption,
        meta.total_skipped_zero_stock,
    )

    return OverstockOutput(overstock_flags=flags, meta=meta)


def write_overstock_output(
    output: OverstockOutput,
    path: str | Path | None = None,
) -> Path:
    """Serialize OverstockOutput to JSON and write to disk.

    Parameters
    ----------
    output : OverstockOutput
        The batch result to write.
    path : str | Path | None
        Output path. Defaults to data/module4_output.json.

    Returns
    -------
    Path
        The path the file was written to.
    """
    out_path = Path(path) if path else DEFAULT_M4_OUTPUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(output.model_dump(), f, indent=2, default=str)

    logger.info("Overstock output written to %s", out_path)
    return out_path


def load_overstock_output(path: str | Path | None = None) -> OverstockOutput | None:
    """Load the last-written module4_output.json.

    Returns None if the file does not exist or is malformed.
    """
    in_path = Path(path) if path else DEFAULT_M4_OUTPUT_PATH
    if not in_path.exists():
        return None

    try:
        with open(in_path) as f:
            raw = json.load(f)
        return OverstockOutput(**raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to load overstock output from %s: %s", in_path, e)
        return None


def filter_overstock_flags(
    output: OverstockOutput,
    store_id: str | None = None,
    risk_level: str | None = None,
    category: str | None = None,
) -> list[OverstockFlag]:
    """Filter overstock flags by optional criteria."""
    flags = output.overstock_flags
    if store_id:
        flags = [f for f in flags if f.store_id == store_id]
    if risk_level:
        flags = [f for f in flags if f.risk_level == risk_level]
    if category:
        flags = [f for f in flags if f.category == category]
    return flags