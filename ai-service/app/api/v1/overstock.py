"""M4 — Overstock detection endpoints.

POST /api/v1/overstock/run   — triggers the batch calculation, writes output
GET  /api/v1/overstock       — reads last-written output, returns filtered flags
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.overstock import (
    OverstockRequest,
    OverstockResponse,
    OverstockApiFlag,
    OverstockApiResponse,
    OverstockRunResponse,
)
from app.services.overstock_service import (
    run_overstock_batch,
    write_overstock_output,
    load_overstock_output,
    filter_overstock_flags,
)
from app.core.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/overstock", tags=["overstock"], dependencies=[Depends(verify_internal_token)])


# ── Legacy endpoint (unchanged, kept for backward compatibility) ────


@router.post("/detect", response_model=OverstockResponse)
def detect_overstock(request: OverstockRequest, db: Session = Depends(get_db)):
    """Legacy overstock detection endpoint — kept for backward compatibility.

    This will be replaced by the batch-based /run endpoint once the
    nightly pipeline is fully wired.
    """
    from app.services.overstock_service_legacy import OverstockService
    service = OverstockService(db)
    return service.detect(product_id=request.product_id, store_id=request.store_id)


# ── M4 batch endpoints ──────────────────────────────────────────────


@router.post("/run", response_model=OverstockRunResponse)
def run_overstock_batch_endpoint():
    """Trigger the M4 overstock detection batch calculation.

    Reads from:
      - data/module1_output.json (M1 consumption profiles)
      - data/module1_input.json  (stock + catalog)
      - data/module5_output.json (M5 velocity tiers)

    Writes to:
      - data/module4_output.json

    Returns the meta summary.
    """
    logger.info("M4 batch triggered via API")

    try:
        output = run_overstock_batch()
        write_overstock_output(output)

        logger.info(
            "M4 batch complete: %d evaluated, %d high, %d medium",
            output.meta.total_evaluated,
            output.meta.total_flagged_high,
            output.meta.total_flagged_medium,
        )

        return OverstockRunResponse(success=True, meta=output.meta)
    except FileNotFoundError as e:
        logger.error("M4 batch failed: %s", e)
        raise NotFoundError(detail=str(e))
    except Exception as e:
        logger.error("M4 batch failed unexpectedly: %s", e)
        raise


@router.get("", response_model=OverstockApiResponse)
def get_overstock_flags(
    store_id: str | None = Query(None, description="Filter by store ID"),
    risk_level: str | None = Query(None, description="Filter by risk level (high | medium | low | dead_zero_velocity)"),
    category: str | None = Query(None, description="Filter by product category"),
):
    """Read the last-written overstock flags with optional filtering.

    This is what the FE Products list / Daily Report queries.
    """
    output = load_overstock_output()
    if output is None:
        raise NotFoundError(
            detail="No overstock data found. Run POST /api/v1/overstock/run first."
        )

    filtered = filter_overstock_flags(
        output,
        store_id=store_id,
        risk_level=risk_level,
        category=category,
    )

    api_flags = [
        OverstockApiFlag(
            product_id=f.product_id,
            store_id=f.store_id,
            category=f.category,
            current_stock=f.current_stock,
            average_daily_sales=f.average_daily_sales,
            days_of_supply=f.days_of_supply,
            risk_level=f.risk_level,
            suggested_action=f.suggested_action,
            tier=f.tier,
            stock_data_stale=f.stock_data_stale,
            insufficient_data=f.insufficient_data,
            computed_at=f.computed_at,
        )
        for f in filtered
    ]

    return OverstockApiResponse(flags=api_flags, total=len(api_flags))