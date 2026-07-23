# Satellite Telemetry Dashboard

Local-only proof of concept for viewing and managing satellite telemetry. The repository contains a Flask REST API, a React/Vite dashboard, automated tests, and a Docker Compose setup.

## Architecture

```text
Browser :3000 (React + Nginx)
        │ /api proxy
        ▼
Flask API :5001 host / :5000 container ── TelemetryService ── SQLite :memory:
```

The API stores data in a process-local SQLite in-memory database. `satelliteId` is the telemetry table primary key, so each satellite can have only one current telemetry row and no separate generated `id` is returned. Records remain available while the API process is running and are intentionally reset to the 20 seeded satellites (`RL-001` through `RL-020`) when it restarts. Docker runs one Gunicorn worker because multiple workers would each receive a separate in-memory database.

## Quick start with Docker

Requirements: Docker and Docker Compose.

```bash
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The direct API is available at [http://localhost:5001](http://localhost:5001).

Stop the services with `Ctrl+C`, or run `docker compose down` from another terminal.

To change ports, copy `.env.example` to `.env` and edit the values.

## Local development without Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
flask --app wsgi run --debug --port 5001
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` requests to the Flask server.

## API

### `GET /telemetry`

Optional query parameters:

- `satelliteId`: exact satellite ID filter.
- `status`: `healthy`, `degraded`, or `critical`.
- `page`: one-based page number; defaults to `1`.
- `pageSize`: defaults to `10`, maximum `100`.
- `sortBy`: `timestamp`, `altitude`, `velocity`, `satelliteId`, or `status`.
- `sortOrder`: `asc` or `desc`; defaults to `desc`.

```bash
curl 'http://localhost:5001/telemetry?status=healthy&page=1&pageSize=10&sortBy=timestamp&sortOrder=desc'
```

### `POST /telemetry`

The request body must be JSON with all five fields:

| Field | Accepted format |
| --- | --- |
| `satelliteId` | Non-empty string, trimmed, maximum 64 characters, primary key and unique in the database |
| `timestamp` | ISO 8601 date and time, such as `2026-07-23T19:00:00Z`; date-only values are rejected |
| `altitude` | JSON number greater than zero; decimals such as `11.11` are valid |
| `velocity` | JSON number greater than zero; decimals such as `0.001` are valid |
| `status` | One of `healthy`, `degraded`, or `critical` |

Altitude and velocity must be JSON numbers, not quoted strings. Use `11.11`, not `"11.11"`. Values must be finite; `0`, negative values, `NaN`, and infinity are rejected. The dashboard accepts decimal text input and converts it to a JSON number before submitting.

```bash
curl -X POST http://localhost:5001/telemetry \
  -H 'Content-Type: application/json' \
  -d '{
    "satelliteId": "RL-021",
    "timestamp": "2026-07-23T19:00:00Z",
    "altitude": 450.5,
    "velocity": 7.7,
    "status": "healthy"
  }'
```

Timestamps without a timezone are interpreted as UTC and all responses are normalized to UTC with a trailing `Z`. Status values are normalized to lowercase. A successful create returns `201 Created`; attempting to reuse an existing `satelliteId` returns `409 Conflict` with error code `duplicate_satellite_id`.

Validation and conflict errors use this structure:

```json
{
  "error": {
    "code": "validation_error",
    "message": "altitude must be a finite JSON number greater than zero.",
    "fields": {
      "altitude": "must be a finite JSON number greater than zero"
    }
  }
}
```

### `GET /telemetry/<satelliteId>` and `DELETE /telemetry/<satelliteId>`

These retrieve or delete one telemetry record using its `satelliteId`. A successful delete returns `204 No Content`.

## Tests

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run build
```

The test suites cover CRUD behavior, filtering, pagination, sorting, validation, error responses, loading/error UI, form validation, and deletion.

## Assumptions and future work

- Demo seed data is enabled by default and can be disabled with `SEED_DEMO_DATA=false`.
- Each startup creates a fresh in-memory dataset containing one row for every satellite from `RL-001` through `RL-020`. Runtime additions and deletions are discarded when the API process or container stops.
- Docker maps the container API port `5000` to host port `5001` by default because macOS `ControlCenter` commonly occupies host port `5000`. Override this with `BACKEND_PORT` in `.env` if needed.
- Authentication, authorization, persistent storage, telemetry ingestion, cloud deployment, CI/CD, and production observability are intentionally out of scope for this local POC.
- `test.pdf` and other PDFs are ignored so take-home artifacts are not committed accidentally.

# Time Spend
- To spin up the POC for the Backend and Frontend, it took me about 2 hours