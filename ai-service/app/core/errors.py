"""Shared exception classes mapped to { "error": {...} } responses."""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application-level errors."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "bad_request",
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND, error_code="not_found")


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation failed") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, error_code="validation_error")


class ServiceUnavailableError(AppException):
    def __init__(self, detail: str = "Service temporarily unavailable") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, error_code="service_unavailable")


class InsufficientDataError(AppException):
    def __init__(self, detail: str = "Insufficient data to perform analysis") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, error_code="insufficient_data")