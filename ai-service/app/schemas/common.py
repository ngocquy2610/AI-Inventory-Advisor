"""Shared Pydantic models: ErrorResponse, Pagination, etc."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Pagination(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ai-inventory-advisor"
    version: str = "1.0.0"