"""Explanation schemas."""

from uuid import UUID

from pydantic import BaseModel


class ExplainRequest(BaseModel):
    explainable_type: str
    explainable_id: UUID


class ExplainResponse(BaseModel):
    explainable_type: str
    explainable_id: UUID
    summary: str
    details: dict | None = None
    confidence: str | None = None
    model_used: str | None = None