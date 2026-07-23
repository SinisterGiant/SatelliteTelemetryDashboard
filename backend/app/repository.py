"""SQLite-backed telemetry persistence.

The repository owns the database connection and keeps SQL out of the HTTP and
validation layers. A single shared in-memory connection is intentional: SQLite
`:memory:` databases are otherwise isolated per connection. Access is guarded
by a re-entrant lock so the Flask development server and Gunicorn threads can
share the process-local store safely.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from threading import RLock
from typing import Iterable

from .errors import ConflictError
from .models import TelemetryEntry


class TelemetryRepository:
    """Repository for runtime-only telemetry records."""

    _sort_columns = {
        "timestamp": "timestamp",
        "altitude": "altitude",
        "velocity": "velocity",
        "satelliteId": "satellite_id",
        "status": "status",
    }

    def __init__(self, database_path: str = ":memory:") -> None:
        self._lock = RLock()
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    satellite_id TEXT NOT NULL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    altitude REAL NOT NULL CHECK (altitude > 0),
                    velocity REAL NOT NULL CHECK (velocity > 0),
                    status TEXT NOT NULL CHECK (status IN ('healthy', 'degraded', 'critical'))
                )
                """
            )

    @staticmethod
    def _to_entry(row: sqlite3.Row) -> TelemetryEntry:
        return TelemetryEntry(
            satellite_id=row["satellite_id"],
            timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
            altitude=float(row["altitude"]),
            velocity=float(row["velocity"]),
            status=row["status"],
        )

    def create(self, entry: TelemetryEntry) -> TelemetryEntry:
        try:
            with self._lock, self._connection:
                cursor = self._connection.execute(
                    """
                    INSERT INTO telemetry (satellite_id, timestamp, altitude, velocity, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        entry.satellite_id,
                        entry.timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        entry.altitude,
                        entry.velocity,
                        entry.status,
                    ),
                )
                row = self._connection.execute(
                    "SELECT * FROM telemetry WHERE satellite_id = ?", (entry.satellite_id,)
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            if "telemetry.satellite_id" in str(exc):
                raise ConflictError(
                    f"Satellite ID {entry.satellite_id} already exists.",
                    code="duplicate_satellite_id",
                    fields={"satelliteId": "must be unique"},
                ) from exc
            raise
        assert row is not None
        return self._to_entry(row)

    def get(self, satellite_id: str) -> TelemetryEntry | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM telemetry WHERE satellite_id = ?", (satellite_id,)
            ).fetchone()
        return self._to_entry(row) if row else None

    def list(
        self,
        *,
        satellite_id: str | None,
        status: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[TelemetryEntry], int]:
        where: list[str] = []
        values: list[str | int] = []
        if satellite_id:
            where.append("satellite_id = ?")
            values.append(satellite_id)
        if status:
            where.append("status = ?")
            values.append(status)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        order_column = self._sort_columns[sort_by]
        direction = "DESC" if sort_order == "desc" else "ASC"
        offset = (page - 1) * page_size

        with self._lock:
            total = self._connection.execute(
                f"SELECT COUNT(*) FROM telemetry {where_sql}", values
            ).fetchone()[0]
            rows = self._connection.execute(
                f"""
                SELECT * FROM telemetry
                {where_sql}
                ORDER BY {order_column} {direction}, satellite_id ASC
                LIMIT ? OFFSET ?
                """,
                [*values, page_size, offset],
            ).fetchall()
        return [self._to_entry(row) for row in rows], int(total)

    def delete(self, satellite_id: str) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM telemetry WHERE satellite_id = ?", (satellite_id,)
            )
        return cursor.rowcount > 0

    def count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0])

    def seed(self, entries: Iterable[TelemetryEntry]) -> None:
        for entry in entries:
            self.create(entry)

    def close(self) -> None:
        with self._lock:
            self._connection.close()
