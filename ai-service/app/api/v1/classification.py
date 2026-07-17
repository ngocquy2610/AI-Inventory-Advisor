"""M5 — POST /api/v1/classify (velocity tiers) + existing ABC/XYZ endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db, verify_internal_token
from app.schemas.classification import (
    ClassificationRequest,
    ClassificationResponse,
    ClassificationBatchOutput,
    ConsumptionMetric,
)
from app.services.classification_service import (
    ClassificationService,
    classify_batch,
    load_previous_tiers_from_file,
)
from app.data_access.product_lookup import load_product_categories
from app.data_access.thresholds_loader import (
    load_classification_thresholds,
    load_classification_config,
)

router = APIRouter(prefix="/classify", tags=["classification"], dependencies=[Depends(verify_internal_token)])


# ── Existing ABC/XYZ endpoint (unchanged) ──────────────────────────


@router.post("", response_model=ClassificationResponse)
def classify_products(request: ClassificationRequest, db: Session = Depends(get_db)):
    service = ClassificationService(db)
    return service.classify(product_id=request.product_id, store_id=request.store_id)


# ── New M5 velocity classification endpoint ────────────────────────


class VelocityClassifyRequest(BaseModel):
    """Batch payload from Rails — includes category directly.

    Once BE integration is wired up, category comes from Rails rather
    than the local products.json stub.
    """
    metrics: list[ConsumptionMetric]
    category_map: dict[str, str] | None = None  # product_id → category; optional


@router.post("/velocity", response_model=ClassificationBatchOutput)
def classify_velocity(
    request: VelocityClassifyRequest,
    db: Session = Depends(get_db),
):
    """Classify product-store combinations into velocity tiers.

    Accepts a batch of consumption metrics (from M1) and optional
    category map. If category_map is not provided, falls back to
    the local product catalog derived from M1 data files.
    """
    category_map = request.category_map
    if category_map is None:
        category_map = load_product_categories()

    thresholds = load_classification_thresholds()
    config = load_classification_config()

    # In production, previous tiers come from the DB; for now use file
    previous_tiers = load_previous_tiers_from_file("data/module5_output.json")

    return classify_batch(
        metrics=request.metrics,
        category_map=category_map,
        thresholds=thresholds,
        config=config,
        previous_tiers=previous_tiers,
    )