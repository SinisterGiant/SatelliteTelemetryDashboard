"""Application-specific exceptions and error payload helpers."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base error that can be safely translated into an API response."""

    status_code = 500
    code = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code or self.status_code
        self.code = code or self.code
        self.fields = fields or {}


class ValidationError(AppError):
    """Raised when a request cannot be accepted."""

    status_code = 400
    code = "validation_error"


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """Raised when a request conflicts with an existing resource."""

    status_code = 409
    code = "conflict"
