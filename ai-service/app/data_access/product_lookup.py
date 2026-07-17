"""Product category lookup — derived from M1 data products.json merged files.

This module reads module1_output.json to obtain the set of product IDs
that were analysed, then looks up their details (including category) from
module1_input.json. The old data/products.json stub is no longer used and
is deleted after a successful load.

Once the Rails BE integration is wired up, this whole module is replaced
with a call that receives category directly in the API payload (or fetches
it from the product catalog API).

Open decision (see services/README.md):
    category is stubbed from data/products.json locally; swap to the
    real BE-supplied field before Phase 2 sign-off.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_M1_OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "module1_output.json"
DEFAULT_M1_INPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "module1_input.json"
DEFAULT_PRODUCTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "products.json"


def load_product_categories(
    m1_output_path: str | Path | None = None,
    m1_input_path: str | Path | None = None,
) -> dict[str, str]:
    """Build product_id → category mapping from M1 data.

    The product IDs come from module1_output.json (only products that were
    actually analysed), and the category comes from module1_input.json.

    Once the mapping is successfully built, the old data/products.json stub
    is deleted if it still exists.

    Raises
    ------
    FileNotFoundError
        If either module1_output.json or module1_input.json does not exist.
    KeyError
        If a product ID from module1_output has no matching entry in
        module1_input — this should never happen with valid data.
    """
    m1_output_path = Path(m1_output_path) if m1_output_path else DEFAULT_M1_OUTPUT_PATH
    m1_input_path = Path(m1_input_path) if m1_input_path else DEFAULT_M1_INPUT_PATH

    if not m1_output_path.exists():
        raise FileNotFoundError(f"M1 output not found at {m1_output_path}")
    if not m1_input_path.exists():
        raise FileNotFoundError(f"M1 input not found at {m1_input_path}")

    # Step 1: Collect unique product IDs from module1_output.json
    with open(m1_output_path) as f:
        m1_output = json.load(f)

    product_ids: set[str] = set()
    for profile in m1_output.get("profiles", []):
        pid = profile.get("product_id")
        if pid:
            product_ids.add(pid)

    logger.info("Found %d unique product IDs in %s", len(product_ids), m1_output_path)

    # Step 2: Load product catalog from module1_input.json
    with open(m1_input_path) as f:
        m1_input = json.load(f)

    products = m1_input.get("products", [])
    catalog: dict[str, dict] = {p["id"]: p for p in products}

    # Step 3: Build the mapping
    mapping: dict[str, str] = {}
    for pid in sorted(product_ids):
        if pid not in catalog:
            raise KeyError(
                f"Product '{pid}' from M1 output has no matching entry in "
                f"module1_input.json. Check that the product catalog is up to date."
            )
        cat = catalog[pid].get("category", "default")
        mapping[pid] = cat

    logger.info("Built %d product category mappings from M1 data", len(mapping))

    # Step 4: Clean up the old products.json stub (no longer needed)
    products_path = Path(m1_input_path).parent / "products.json"
    if products_path.exists():
        try:
            os.remove(products_path)
            logger.info("Removed old products.json stub at %s", products_path)
        except OSError as e:
            logger.warning("Could not remove products.json: %s", e)

    return mapping


def get_category(
    product_id: str,
    mapping: dict[str, str],
) -> str:
    """Look up a single product's category, raising on missing entry.

    A missing product_id is a hard error — never silently fall through
    to 'default' without being explicit about it.
    """
    if product_id not in mapping:
        raise KeyError(
            f"Product '{product_id}' has no category mapping. "
            "Ensure the product exists in module1_input.json and was "
            "analysed by M1."
        )
    return mapping[product_id]