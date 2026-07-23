"""HTTP routes for the telemetry API."""

from __future__ import annotations

from math import ceil

from flask import Blueprint, current_app, jsonify, request

from .errors import ValidationError
from .service import TelemetryService


telemetry_blueprint = Blueprint("telemetry", __name__)


def _service() -> TelemetryService:
    return current_app.extensions["telemetry_service"]


def _json_body() -> object:
    if not request.is_json:
        raise ValidationError("Content-Type must be application/json.")
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Request body must contain valid JSON.")
    return payload


@telemetry_blueprint.get("/telemetry")
def list_telemetry():
    entries, total, status_counts, page, page_size, sort_by, sort_order = _service().list(
        satellite_id=request.args.get("satelliteId"),
        status=request.args.get("status"),
        page_value=request.args.get("page"),
        page_size_value=request.args.get("pageSize"),
        sort_by=request.args.get("sortBy"),
        sort_order=request.args.get("sortOrder"),
    )
    return jsonify(
        data=[entry.to_dict() for entry in entries],
        pagination={
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": ceil(total / page_size) if total else 0,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        },
        summary=status_counts,
    )


@telemetry_blueprint.post("/telemetry")
def create_telemetry():
    entry = _service().create(_json_body())
    response = jsonify(data=entry.to_dict())
    response.status_code = 201
    response.headers["Location"] = f"/telemetry/{entry.satellite_id}"
    return response


@telemetry_blueprint.get("/telemetry/<satellite_id>")
def get_telemetry(satellite_id: str):
    return jsonify(data=_service().get(satellite_id).to_dict())


@telemetry_blueprint.delete("/telemetry/<satellite_id>")
def delete_telemetry(satellite_id: str):
    _service().delete(satellite_id)
    return "", 204
