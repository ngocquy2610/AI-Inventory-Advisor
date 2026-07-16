"""Chat schemas."""

from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: UUID
    message: str


class ChatResponse(BaseModel):
    session_id: UUID
    reply: str
    sources: list[str] | None = None