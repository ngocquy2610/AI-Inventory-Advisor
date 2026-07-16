"""Supplier reliability service — M8 logic."""

import numpy as np
from sqlalchemy.orm import Session

from app.schemas.supplier import SupplierReliabilityResponse, SupplierReliabilityResult


class SupplierService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def analyze_reliability(self, supplier_id=None) -> SupplierReliabilityResponse:
        # Generate synthetic supplier reliability data
        if supplier_id:
            return SupplierReliabilityResponse(
                suppliers=[
                    SupplierReliabilityResult(
                        supplier_id=supplier_id,
                        supplier_name="Sample Supplier",
                        on_time_delivery_rate=float(np.random.uniform(0.85, 0.99)),
                        quality_score=float(np.random.uniform(0.9, 1.0)),
                        lead_time_days=float(np.random.uniform(3, 14)),
                        lead_time_variability=float(np.random.uniform(0.5, 3)),
                        fill_rate=float(np.random.uniform(0.9, 1.0)),
                        overall_reliability_score=float(np.random.uniform(0.8, 1.0)),
                        risk_level=np.random.choice(["low", "medium", "high"], p=[0.6, 0.3, 0.1]),
                    )
                ],
                total_items=1,
            )

        suppliers = []
        for i in range(5):
            suppliers.append(
                SupplierReliabilityResult(
                    supplier_id=f"00000000-0000-0000-0000-0000000000{i+1:02d}",
                    supplier_name=f"Supplier {i+1}",
                    on_time_delivery_rate=float(np.random.uniform(0.8, 0.99)),
                    quality_score=float(np.random.uniform(0.85, 1.0)),
                    lead_time_days=float(np.random.uniform(2, 15)),
                    lead_time_variability=float(np.random.uniform(0.5, 4)),
                    fill_rate=float(np.random.uniform(0.85, 1.0)),
                    overall_reliability_score=float(np.random.uniform(0.75, 1.0)),
                    risk_level=np.random.choice(["low", "medium", "high"], p=[0.5, 0.35, 0.15]),
                )
            )
        return SupplierReliabilityResponse(suppliers=suppliers, total_items=len(suppliers))