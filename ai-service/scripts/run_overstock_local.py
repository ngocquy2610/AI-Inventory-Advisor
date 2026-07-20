#!/usr/bin/env python3
"""CLI runner for local M4 development — no FastAPI needed.

Reads data/module1_output.json + data/module1_input.json + data/module5_output.json,
runs run_overstock_batch(), writes data/module4_output.json, and prints a
short summary table to stdout.

Usage:
    python scripts/run_overstock_local.py [--m1-output-path PATH] [--m1-input-path PATH] [--m5-output-path PATH] [--output-path PATH]
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

from app.services.overstock_service import (
    run_overstock_batch,
    write_overstock_output,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_overstock_local")

DEFAULT_M4_OUTPUT = _PROJECT_ROOT / "data" / "module4_output.json"


def print_summary(output, output_path: Path) -> None:
    """Print a short summary table to stdout."""
    flags = output.overstock_flags
    meta = output.meta

    print()
    print("=" * 60)
    print("M4 — Overstock Detection Complete")
    print("=" * 60)
    print(f"  Source files:")
    for sf in meta.source_files:
        print(f"    • {sf}")
    print(f"  Output:     {output_path}")
    print(f"  Evaluated:  {meta.total_evaluated} product-store combinations")
    print(f"  Flagged high:   {meta.total_flagged_high}")
    print(f"  Flagged medium: {meta.total_flagged_medium}")
    print(f"  Dead (zero velocity): {meta.total_dead_zero_velocity}")
    print(f"  Skipped insufficient_data: {meta.total_skipped_insufficient_data}")
    print(f"  Skipped missing consumption: {meta.total_skipped_missing_consumption}")
    print(f"  Skipped zero stock: {meta.total_skipped_zero_stock}")
    print()

    # Risk level counts
    risk_counts: dict[str, int] = {}
    for f in flags:
        risk_counts[f.risk_level] = risk_counts.get(f.risk_level, 0) + 1

    print(f"  {'Risk Level':<22} {'Count':<8}")
    print(f"  {'-'*22} {'-'*8}")
    for level in ("high", "medium", "low", "dead_zero_velocity"):
        cnt = risk_counts.get(level, 0)
        print(f"  {level:<22} {cnt:<8}")
    print(f"  {'-'*22} {'-'*8}")
    print(f"  {'Total':<22} {meta.total_evaluated:<8}")
    print()

    # Show first 5 as sample
    print("  Sample flags (first 5):")
    print(f"  {'Product':<12} {'Store':<12} {'Category':<14} {'DOS':<10} {'Risk':<18} {'Action':<14}")
    print(f"  {'-'*12} {'-'*12} {'-'*14} {'-'*10} {'-'*18} {'-'*14}")
    for f in flags[:5]:
        dos_str = f"{f.days_of_supply}" if f.days_of_supply is not None else "null"
        action_str = f.suggested_action if f.suggested_action else "—"
        stale_mark = " ⚠️ stale" if f.stock_data_stale else ""
        print(f"  {f.product_id:<12} {f.store_id:<12} {f.category:<14} {dos_str:<10} {f.risk_level:<18}{stale_mark} {action_str:<14}")
    if len(flags) > 5:
        print(f"  ... and {len(flags) - 5} more")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M4 Overstock Detection locally")
    parser.add_argument("--m1-output-path", default=None, help="Path to module1_output.json")
    parser.add_argument("--m1-input-path", default=None, help="Path to module1_input.json")
    parser.add_argument("--m5-output-path", default=None, help="Path to module5_output.json")
    parser.add_argument("--output-path", default=str(DEFAULT_M4_OUTPUT), help="Output path for module4_output.json")
    args = parser.parse_args()

    # Run the batch
    logger.info("Running M4 overstock detection...")
    output = run_overstock_batch(
        m1_output_path=args.m1_output_path,
        m1_input_path=args.m1_input_path,
        m5_output_path=args.m5_output_path,
    )

    # Write output
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_overstock_output(output, path=output_path)
    logger.info("Output written to %s", output_path)

    # Print summary
    print_summary(output, output_path)


if __name__ == "__main__":
    main()