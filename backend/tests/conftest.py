import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app({"TESTING": True, "SEED_DEMO_DATA": False})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def telemetry_payload():
    return {
        "satelliteId": "RL-TEST",
        "timestamp": "2026-07-23T12:00:00-07:00",
        "altitude": 450.5,
        "velocity": 7.7,
        "status": "healthy",
    }
