"""
Custom application exception hierarchy.

All domain exceptions inherit from AppException which carries an HTTP status
code and an error code string. The global error handler converts these into
the standard API error response format.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base class for all application-level exceptions.

    Attributes:
        status_code: HTTP status code to return to the client.
        code: Machine-readable error code (e.g. "NOT_FOUND").
        message: Human-readable description.
        details: Optional structured details (validation errors, etc.).
    """

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        details: Optional[Any] = None,
    ) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)


class UnauthorizedException(AppException):
    """Raised when authentication fails or is missing."""

    status_code = 401
    code = "UNAUTHORIZED"

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


class ForbiddenException(AppException):
    """Raised when the authenticated user lacks permission for the action."""

    status_code = 403
    code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission to perform this action") -> None:
        super().__init__(message)


class ConflictException(AppException):
    """Raised when a resource already exists (duplicate key, etc.)."""

    status_code = 409
    code = "CONFLICT"

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message)


class ValidationException(AppException):
    """Raised when business-level validation fails (beyond Pydantic schema checks)."""

    status_code = 422
    code = "VALIDATION_ERROR"

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, details)


class ExternalServiceException(AppException):
    """Raised when a call to an external service (WhatsApp API, etc.) fails."""

    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, service: str, message: str = "External service error") -> None:
        super().__init__(f"{service}: {message}")
        self.service = service
