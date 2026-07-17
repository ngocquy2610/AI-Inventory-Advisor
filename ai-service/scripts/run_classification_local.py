#!/usr/bin/env python3
"""CLI runner for local M5 development — no FastAPI needed.

Reads data/module1_output.json + data/module1_input.json + threshold configs,
runs classify_batch(), writes data/module5_output.json, and prints a
short summary table to stdout.

Usage:
    python scripts/run_classification_local.py [--m1-output-path PATH] [--m1-input-path PATH] [--output-path PATH]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure the project root is on the path
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.data_access.module1_loader import load_module1_metrics
from app.data_access.product_lookup import load_product_categories
from app.data_access.thresholds_loader import load_classification_thresholds, load_classification_config
from app.services.classification_service import classify_batch, load_previous_tiers_from_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_classification_local")

DEFAULT_M5_OUTPUT = _PROJECT_ROOT / "data" / "module5_output.json"


def print_summary(output, output_path: Path) -> None:
    """Print a short summary table to stdout."""
    classifications = output.classifications
    total = len(classifications)
    meta = output.meta

    print()
    print("=" * 60)
    print("M5 — Product Classification Complete")
    print("=" * 60)
    print(f"  Source:     {meta.source_file}")
    print(f"  Output:     {output_path}")
    print(f"  Total:      {total} product-store combinations")
    print(f"  Classified: {meta.total_classified}")
    print(f"  Insufficient data: {meta.total_insufficient_data}")
    print()

    # Tier counts
    tier_counts: dict[str, int] = {}
    for c in classifications:
        if c.tier is not None:
            tier_counts[c.tier] = tier_counts.get(c.tier, 0) + 1

    print(f"  {'Tier':<12} {'Count':<8}")
    print(f"  {'-'*12} {'-'*8}")
    for tier in ("fast", "medium", "slow", "dead"):
        cnt = tier_counts.get(tier, 0)
        print(f"  {tier:<12} {cnt:<8}")
    null_count = meta.total_insufficient_data
    if null_count:
        print(f"  {'null (insuff)':<12} {null_count:<8}")
    print(f"  {'-'*12} {'-'*8}")
    print(f"  {'Total':<12} {total:<8}")
    print()

    # Show first 5 as sample
    print("  Sample classifications (first 5):")
    print(f"  {'Product':<12} {'Store':<12} {'Category':<14} {'Tier':<10} {'Changed':<8} {'DaysSince':<10}")
    print(f"  {'-'*12} {'-'*12} {'-'*14} {'-'*10} {'-'*8} {'-'*10}")
    for c in classifications[:5]:
        changed_str = "✓" if c.tier_changed else "—"
        tier_str = c.tier if c.tier is not None else "null"
        print(f"  {c.product_id:<12} {c.store_id:<12} {c.category:<14} {tier_str:<10} {changed_str:<8} {c.days_since_last_sale:<10}")
    if total > 5:
        print(f"  ... and {total - 5} more")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M5 Product Classification locally")
    parser.add_argument("--m1-output-path", default=None, help="Path to module1_output.json")
    parser.add_argument("--m1-input-path", default=None, help="Path to module1_input.json")
    parser.add_argument("--thresholds-path", default=None, help="Path to classification_thresholds.json")
    parser.add_argument("--config-path", default=None, help="Path to classification_config.json")
    parser.add_argument("--output-path", default=str(DEFAULT_M5_OUTPUT), help="Output path for module5_output.json")
    parser.add_argument("--previous-path", default=None, help="Path to previous module5_output.json for tier_changed detection")
    args = parser.parse_args()

    # Load inputs
    logger.info("Loading M1 consumption metrics...")
    metrics = load_module1_metrics(args.m1_output_path)
    logger.info("  → %d metrics loaded", len(metrics))

    logger.info("Loading product categories from M1 data...")
    category_map = load_product_categories(
        m1_output_path=args.m1_output_path,
        m1_input_path=args.m1_input_path,
    )
    logger.info("  → %d categories loaded", len(category_map))

    logger.info("Loading classification thresholds...")
    thresholds = load_classification_thresholds(args.thresholds_path)

    logger.info("Loading classification config...")
    config = load_classification_config(args.config_path)

    # Load previous tiers for tier_changed detection
    prev_path = args.previous_path or str(DEFAULT_M5_OUTPUT)
    previous_tiers = load_previous_tiers_from_file(prev_path)

    # Run classification
    logger.info("Running classification...")
    output = classify_batch(
        metrics=metrics,
        category_map=category_map,
        thresholds=thresholds,
        config=config,
        previous_tiers=previous_tiers,
    )

    # Write output
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output.model_dump(), f, indent=2, default=str)
    logger.info("Output written to %s", output_path)

    # Print summary
    print_summary(output, output_path)


if __name__ == "__main__":
    main()