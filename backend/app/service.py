"""Telemetry validation and application services."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from .errors import NotFoundError, ValidationError
from .models import TelemetryEntry
from .repository import TelemetryRepository


ALLOWED_STATUSES = ("healthy", "degraded", "critical")
ALLOWED_SORT_FIELDS = ("timestamp", "altitude", "velocity", "satelliteId", "status")


class TelemetryService:
    """Coordinates request validation and repository operations."""

    def __init__(self, repository: TelemetryRepository) -> None:
        self._repository = repository

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                "timestamp must be an ISO 8601 datetime.",
                fields={"timestamp": "must be a non-empty ISO 8601 datetime"},
            )
        if "T" not in value.strip() and " " not in value.strip():
            raise ValidationError(
                "timestamp must be an ISO 8601 datetime.",
                fields={"timestamp": "must include a date and time"},
            )
        try:
            normalized = value.strip().replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValidationError(
                "timestamp must be an ISO 8601 datetime.",
                fields={"timestamp": "must be a valid ISO 8601 datetime"},
            ) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _parse_positive_number(value: Any, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(
                f"{field_name} must be a finite JSON number greater than zero.",
                fields={field_name: "must be a finite JSON number greater than zero"},
            )
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValidationError(
                f"{field_name} must be a positive number.",
                fields={field_name: "must be a finite number greater than zero"},
            )
        return number

    @classmethod
    def _entry_from_payload(cls, payload: Any) -> TelemetryEntry:
        if not isinstance(payload, dict):
            raise ValidationError("Request body must be a JSON object.")

        required = ("satelliteId", "timestamp", "altitude", "velocity", "status")
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValidationError(
                "Request body is missing required fields.",
                fields={field: "is required" for field in missing},
            )

        satellite_id = payload["satelliteId"]
        if not isinstance(satellite_id, str) or not satellite_id.strip():
            raise ValidationError(
                "satelliteId must be a non-empty string.",
                fields={"satelliteId": "must be a non-empty string"},
            )
        satellite_id = satellite_id.strip()
        if len(satellite_id) > 64:
            raise ValidationError(
                "satelliteId must be 64 characters or fewer.",
                fields={"satelliteId": "must be 64 characters or fewer"},
            )

        status = payload["status"]
        if not isinstance(status, str) or status.strip().lower() not in ALLOWED_STATUSES:
            allowed = ", ".join(ALLOWED_STATUSES)
            raise ValidationError(
                f"status must be one of: {allowed}.",
                fields={"status": f"must be one of {allowed}"},
            )

        return TelemetryEntry(
            satellite_id=satellite_id,
            timestamp=cls._parse_timestamp(payload["timestamp"]),
            altitude=cls._parse_positive_number(payload["altitude"], "altitude"),
            velocity=cls._parse_positive_number(payload["velocity"], "velocity"),
            status=status.strip().lower(),
        )

    def create(self, payload: Any) -> TelemetryEntry:
        return self._repository.create(self._entry_from_payload(payload))

    def get(self, satellite_id: str) -> TelemetryEntry:
        entry = self._repository.get(satellite_id)
        if entry is None:
            raise NotFoundError(f"Telemetry entry for satelliteId {satellite_id} was not found.")
        return entry

    def list(
        self,
        *,
        satellite_id: str | None,
        status: str | None,
        page_value: str | None,
        page_size_value: str | None,
        sort_by: str | None,
        sort_order: str | None,
    ) -> tuple[list[TelemetryEntry], int, dict[str, int], int, int, str, str]:
        if satellite_id is not None:
            satellite_id = satellite_id.strip()
            if len(satellite_id) > 64:
                raise ValidationError(
                    "satelliteId must be 64 characters or fewer.",
                    fields={"satelliteId": "must be 64 characters or fewer"},
                )
            satellite_id = satellite_id or None

        if status is not None:
            status = status.strip().lower()
            if status not in ALLOWED_STATUSES:
                raise ValidationError(
                    "status is not supported.",
                    fields={"status": f"must be one of {', '.join(ALLOWED_STATUSES)}"},
                )

        page = self._parse_int(page_value, "page", default=1, minimum=1)
        page_size = self._parse_int(page_size_value, "pageSize", default=10, minimum=1, maximum=100)

        selected_sort = sort_by or "timestamp"
        if selected_sort not in ALLOWED_SORT_FIELDS:
            raise ValidationError(
                "sortBy is not supported.",
                fields={"sortBy": f"must be one of {', '.join(ALLOWED_SORT_FIELDS)}"},
            )
        selected_order = (sort_order or "desc").lower()
        if selected_order not in ("asc", "desc"):
            raise ValidationError(
                "sortOrder must be asc or desc.",
                fields={"sortOrder": "must be asc or desc"},
            )

        entries, total, status_counts = self._repository.list(
            satellite_id=satellite_id,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=selected_sort,
            sort_order=selected_order,
        )
        return entries, total, status_counts, page, page_size, selected_sort, selected_order

    @staticmethod
    def _parse_int(
        value: str | None,
        field_name: str,
        *,
        default: int,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"{field_name} must be an integer.",
                fields={field_name: "must be an integer"},
            ) from exc
        if parsed < minimum or (maximum is not None and parsed > maximum):
            limit = f" between {minimum} and {maximum}" if maximum is not None else f" at least {minimum}"
            raise ValidationError(
                f"{field_name} must be{limit}.",
                fields={field_name: f"must be{limit}"},
            )
        return parsed

    def delete(self, satellite_id: str) -> None:
        if not self._repository.delete(satellite_id):
            raise NotFoundError(f"Telemetry entry for satelliteId {satellite_id} was not found.")
