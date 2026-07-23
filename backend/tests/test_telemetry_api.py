import json

import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_create_and_get_telemetry(client, telemetry_payload):
    created = client.post("/telemetry", json=telemetry_payload)
    assert created.status_code == 201
    assert created.headers["Location"].startswith("/telemetry/")
    entry = created.json["data"]
    assert entry["satelliteId"] == "RL-TEST"
    assert "id" not in entry
    assert entry["timestamp"] == "2026-07-23T19:00:00.000Z"

    fetched = client.get(f"/telemetry/{entry['satelliteId']}")
    assert fetched.status_code == 200
    assert fetched.json["data"] == entry


def test_decimal_measurements_are_valid(client, telemetry_payload):
    response = client.post(
        "/telemetry",
        json={**telemetry_payload, "altitude": 11.11, "velocity": 0.001},
    )
    assert response.status_code == 201
    assert response.json["data"]["altitude"] == 11.11
    assert response.json["data"]["velocity"] == 0.001


def test_filter_pagination_and_sort(client):
    for satellite_id, altitude in (("RL-A", 100), ("RL-B", 300), ("RL-C", 200)):
        response = client.post(
            "/telemetry",
            json={
                "satelliteId": satellite_id,
                "timestamp": "2026-07-23T12:00:00Z",
                "altitude": altitude,
                "velocity": 7,
                "status": "healthy",
            },
        )
        assert response.status_code == 201

    response = client.get(
        "/telemetry?status=healthy&page=1&pageSize=1&sortBy=altitude&sortOrder=desc"
    )
    assert response.status_code == 200
    assert response.json["pagination"]["totalItems"] == 3
    assert response.json["pagination"]["totalPages"] == 3
    assert response.json["summary"] == {"healthy": 3, "degraded": 0, "critical": 0}
    assert response.json["data"][0]["altitude"] == 300

    filtered = client.get("/telemetry?satelliteId=RL-B")
    assert filtered.status_code == 200
    assert filtered.json["pagination"]["totalItems"] == 1
    assert filtered.json["summary"] == {"healthy": 1, "degraded": 0, "critical": 0}
    assert filtered.json["data"][0]["satelliteId"] == "RL-B"


def test_duplicate_satellite_id_is_rejected(client, telemetry_payload):
    assert client.post("/telemetry", json=telemetry_payload).status_code == 201
    response = client.post("/telemetry", json={**telemetry_payload, "altitude": 999})
    assert response.status_code == 409
    assert response.json["error"]["code"] == "duplicate_satellite_id"
    assert response.json["error"]["fields"] == {"satelliteId": "must be unique"}


def test_startup_creates_fresh_unique_seed_dataset():
    from app import create_app

    first_app = create_app({"TESTING": True, "DATABASE_PATH": ":memory:", "SEED_DEMO_DATA": True})
    first_client = first_app.test_client()
    assert first_client.get("/telemetry").json["pagination"]["totalItems"] == 20
    assert first_client.delete("/telemetry/RL-001").status_code == 204
    assert first_client.get("/telemetry").json["pagination"]["totalItems"] == 19

    second_app = create_app({"TESTING": True, "DATABASE_PATH": ":memory:", "SEED_DEMO_DATA": True})
    second_response = second_app.test_client().get("/telemetry")
    second_entries = second_response.json["data"]
    assert len(second_entries) == 10  # Default page size; the full dataset spans two pages.
    assert second_response.json["pagination"]["totalItems"] == 20
    assert second_response.json["pagination"]["totalPages"] == 2
    assert [entry["satelliteId"] for entry in second_entries] == [f"RL-{index:03d}" for index in range(1, 11)]


def test_delete_and_not_found(client, telemetry_payload):
    satellite_id = client.post("/telemetry", json=telemetry_payload).json["data"]["satelliteId"]
    assert client.delete(f"/telemetry/{satellite_id}").status_code == 204
    response = client.delete(f"/telemetry/{satellite_id}")
    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "field,value",
    [
        ("timestamp", "not-a-date"),
        ("timestamp", "2026-07-23"),
        ("altitude", 0),
        ("velocity", -1),
        ("status", "unknown"),
    ],
)
def test_invalid_fields(client, telemetry_payload, field, value):
    telemetry_payload[field] = value
    response = client.post("/telemetry", json=telemetry_payload)
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_error"
    assert field in response.json["error"]["fields"]


@pytest.mark.parametrize("field", ["altitude", "velocity"])
def test_non_finite_numbers_are_rejected(client, telemetry_payload, field):
    telemetry_payload[field] = float("nan")
    response = client.post("/telemetry", json=telemetry_payload)
    assert response.status_code == 400
    assert field in response.json["error"]["fields"]


def test_missing_fields_and_invalid_content_type(client):
    missing = client.post("/telemetry", json={})
    assert missing.status_code == 400
    assert set(missing.json["error"]["fields"]) == {
        "satelliteId",
        "timestamp",
        "altitude",
        "velocity",
        "status",
    }

    invalid_content_type = client.post("/telemetry", data=json.dumps({}))
    assert invalid_content_type.status_code == 400
    assert invalid_content_type.json["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "query",
    ["page=0", "pageSize=101", "sortBy=nope", "sortOrder=sideways"],
)
def test_invalid_query_parameters(client, query):
    response = client.get(f"/telemetry?{query}")
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_error"


def test_unknown_entry_returns_structured_404(client):
    response = client.get("/telemetry/RL-999")
    assert response.status_code == 404
    assert response.json["error"]["fields"] == {}
