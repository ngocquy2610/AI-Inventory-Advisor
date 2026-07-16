"""Strategy generation service — M12 logic. Orchestrates M3+M8+M9 outputs."""

from sqlalchemy.orm import Session

from app.schemas.strategy import StrategyResponse, StrategyAction
from app.services.reorder_service import ReorderService
from app.services.supplier_service import SupplierService
from app.services.transfer_service import TransferService


class StrategyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reorder_svc = ReorderService(db)
        self.supplier_svc = SupplierService(db)
        self.transfer_svc = TransferService(db)

    def generate(self, store_id, strategy_type="comprehensive") -> StrategyResponse:
        # Fetch outputs from sub-services without recomputing them
        reorder_result = self.reorder_svc.recommend(store_id=store_id)
        supplier_result = self.supplier_svc.analyze_reliability()
        transfer_result = self.transfer_svc.recommend(to_store_id=store_id)

        action_items = []

        # Build actions from reorder recommendations
        for rec in reorder_result.recommendations:
            action_items.append(
                StrategyAction(
                    action=f"Reorder product {rec.product_id}: {rec.recommended_quantity:.0f} units",
                    priority=rec.priority or "medium",
                    expected_impact="Prevent stockout",
                    details={"product_id": str(rec.product_id), "quantity": rec.recommended_quantity},
                )
            )

        # Build actions from supplier analysis
        for sup in supplier_result.suppliers:
            if sup.risk_level == "high":
                action_items.append(
                    StrategyAction(
                        action=f"Review supplier {sup.supplier_id} - high risk detected",
                        priority="high",
                        expected_impact="Improve supply chain reliability",
                        details={"supplier_id": str(sup.supplier_id), "risk": sup.risk_level},
                    )
                )

        # Build actions from transfer recommendations
        for tr in transfer_result.recommendations:
            action_items.append(
                StrategyAction(
                    action=f"Transfer {tr.quantity:.0f} units of {tr.product_name} from store {tr.from_store_id} to store {tr.to_store_id}",
                    priority=tr.priority or "medium",
                    expected_impact="Balance inventory across stores",
                    details={"product_id": str(tr.product_id), "quantity": tr.quantity},
                )
            )

        return StrategyResponse(
            store_id=store_id,
            strategy_type=strategy_type,
            title=f"Inventory Strategy for Store {store_id}",
            description="Consolidated strategy combining reorder, supplier, and transfer recommendations.",
            action_items=action_items,
            expected_impact={"stockout_reduction": "15%", "overstock_reduction": "10%"},
            priority="high",
        )