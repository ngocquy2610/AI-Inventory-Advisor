"""Verifies the server-to-server token from Rails."""

from app.config import settings


def verify_service_token(token: str) -> bool:
    """Return True if the provided token matches the configured service token."""
    return token == settings.service_token