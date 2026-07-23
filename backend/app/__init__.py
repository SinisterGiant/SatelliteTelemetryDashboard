"""Flask application factory for the satellite telemetry API."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .errors import AppError
from .models import TelemetryEntry
from .repository import TelemetryRepository
from .routes import telemetry_blueprint
from .service import TelemetryService


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _seed_entries() -> list[TelemetryEntry]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    statuses = ("healthy", "degraded", "critical")
    return [
        TelemetryEntry(
            f"RL-{index:03d}",
            now - timedelta(minutes=(index - 1) * 3 + 2),
            round(390 + index * 8.4, 1),
            round(7.85 - index * 0.02, 2),
            statuses[(index - 1) % len(statuses)],
        )
        for index in range(1, 21)
    ]


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_PATH=os.getenv("DATABASE_PATH", ":memory:"),
        SEED_DEMO_DATA=_env_bool("SEED_DEMO_DATA", True),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"),
    )
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(level=logging.INFO)
    origins = [origin.strip() for origin in app.config["CORS_ORIGINS"].split(",") if origin.strip()]
    CORS(app, origins=origins or "*")

    repository = TelemetryRepository(app.config["DATABASE_PATH"])
    if app.config["SEED_DEMO_DATA"] and repository.count() == 0:
        repository.seed(_seed_entries())
    app.extensions["telemetry_repository"] = repository
    app.extensions["telemetry_service"] = TelemetryService(repository)
    app.register_blueprint(telemetry_blueprint)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify(error={"code": error.code, "message": error.message, "fields": error.fields}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify(
            error={"code": error.name.lower().replace(" ", "_"), "message": error.description, "fields": {}}
        ), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error")
        return jsonify(
            error={"code": "internal_error", "message": "An unexpected error occurred.", "fields": {}}
        ), 500

    return app
