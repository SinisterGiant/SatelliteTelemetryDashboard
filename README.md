# Satellite Telemetry Dashboard

Local-first proof of concept for viewing and managing satellite telemetry. The repository contains a Flask REST API, a React/Vite dashboard, automated tests, a local Docker Compose setup, and an opt-in AWS deployment layer.

## Architecture

```text
Browser :3000 (React + Nginx)
        │ /api proxy
        ▼
Flask API :5001 host / :5000 container ── TelemetryService ── SQLite :memory:

AWS uses the same containers, with immutable images in ECR and a single EC2 instance behind CloudFront. The public CloudFront URL forwards `/api/*` to the frontend Nginx proxy, so the browser continues to make same-origin requests.
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

This local workflow does not require AWS credentials, an AWS account, ECR, or CloudFront.

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

## AWS deployment

The AWS files are additive; they do not replace or modify the local `docker-compose.yml` workflow.

### AWS architecture

```text
Browser HTTPS
     │
     ▼
CloudFront default HTTPS URL
     │ HTTP origin
     ▼
EC2 :80 ── Frontend Nginx ── Backend :5000 ── SQLite :memory:
```

The deployment intentionally uses one EC2 instance because SQLite `:memory:` is process-local. The backend remains a single Gunicorn worker, and the data resets to the 20 demo satellites whenever the backend container restarts. The backend port is not exposed publicly.

### One-time AWS infrastructure

The CloudFormation template creates the EC2 instance, Elastic IP, ECR repositories, Systems Manager access, GitHub Actions OIDC role, and CloudFront distribution. Select a public subnet in the target VPC and run:

```bash
aws cloudformation deploy \
  --profile default \
  --region us-west-2 \
  --stack-name satellite-telemetry-poc \
  --template-file infra/cloudformation.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    VpcId=vpc-xxxxxxxx \
    SubnetId=subnet-xxxxxxxx
```

The deployment uses the configured AWS profile only for the one-time infrastructure operation. GitHub Actions uses the generated OIDC role instead of long-lived or root credentials.

Retrieve the values needed by GitHub Actions:

```bash
aws cloudformation describe-stacks \
  --profile default \
  --region us-west-2 \
  --stack-name satellite-telemetry-poc \
  --query 'Stacks[0].Outputs'
```

Create these GitHub Actions secrets for the `aws-poc` environment:

| Secret | CloudFormation output | Purpose |
| --- | --- | --- |
| `AWS_DEPLOY_ROLE_ARN` | `GitHubActionsRoleArn` | OIDC role assumed by GitHub Actions |
| `AWS_EC2_INSTANCE_ID` | `InstanceId` | EC2 target for Systems Manager deployment |
| `AWS_CLOUDFRONT_DISTRIBUTION_ID` | `CloudFrontDistributionId` | Frontend cache invalidation |

The workflow in `.github/workflows/deploy.yml` builds both existing Dockerfiles, pushes commit-tagged images to ECR, deploys them through Systems Manager, checks `/api/health`, and invalidates the frontend cache. Pushes to `main` trigger deployment; `workflow_dispatch` supports a manual deployment.

The live dashboard URL is the `DashboardUrl` CloudFormation output. CloudFront provides the HTTPS endpoint, while the EC2 origin is intentionally HTTP for this small POC.

### AWS Compose file

`docker-compose.aws.yml` is an AWS-only Compose configuration. It pulls images rather than building locally, maps the frontend to port `80`, and keeps the backend on the internal Compose network. `.env.aws.example` documents the required image variables; it is not needed for local development.

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

The response includes a `summary` object containing status counts across all records matching the current filters, independent of the requested page:

```json
{
  "summary": {
    "healthy": 12,
    "degraded": 5,
    "critical": 3
  }
}
```

The dashboard uses these aggregate counts for the Healthy and Needs Attention cards while the table continues to render only the current page.

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
- The AWS deployment is public and unauthenticated: anyone with the CloudFront URL can create and delete demo telemetry.
- Authentication, authorization, persistent storage, telemetry ingestion, autoscaling, and production observability remain out of scope.
- AWS deployment uses a single EC2 instance and runtime-only SQLite so the local POC behavior remains unchanged.
- CloudFormation and GitHub Actions are optional; local Docker remains the primary developer/test workflow.
- `test.pdf` and other PDFs are ignored so take-home artifacts are not committed accidentally.

# Time Spent
- To spin up the POC for the Backend and Frontend, it took me about 2 hours
- About another hour for the hosting
