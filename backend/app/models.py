"""Domain models returned by the telemetry service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class TelemetryEntry:
    """Immutable representation of one telemetry reading."""

    satellite_id: str
    timestamp: datetime
    altitude: float
    velocity: float
    status: str

    def to_dict(self) -> dict[str, int | float | str | None]:
        """Serialize the domain model using the public API field names."""

        timestamp = self.timestamp.astimezone(timezone.utc).isoformat(timespec="milliseconds")
        return {
            "satelliteId": self.satellite_id,
            "timestamp": timestamp.replace("+00:00", "Z"),
            "altitude": self.altitude,
            "velocity": self.velocity,
            "status": self.status,
        }
