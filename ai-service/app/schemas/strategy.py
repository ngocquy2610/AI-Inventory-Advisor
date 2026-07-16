"""Strategy generation schemas."""

from uuid import UUID

from pydantic import BaseModel


class StrategyRequest(BaseModel):
    store_id: UUID
    strategy_type: str = "comprehensive"


class StrategyAction(BaseModel):
    action: str
    priority: str
    expected_impact: str | None = None
    details: dict | None = None


class StrategyResponse(BaseModel):
    store_id: UUID
    strategy_type: str
    title: str
    description: str | None = None
    action_items: list[StrategyAction] = []
    expected_impact: dict | None = None
    priority: str | None = None