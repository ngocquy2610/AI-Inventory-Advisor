"""Shared dependencies: DB session, auth check, service token verification."""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal

security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_internal_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> None:
    """Verify the server-to-server bearer token from the Rails backend."""
    if settings.environment == "development":
        # Dev mode: skip token check for convenience
        return
    if credentials is None or credentials.credentials != settings.service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )