# Recovery Operations API

A REST API for recording and tracking recovery operations in distributed applications.

An external recovery system decides what to do when an application experiences a failure. This API manages the records associated with those recovery operations, tracks their status, and exposes them to other components.

**Scope:** This project manages recovery-operation records. It does not detect failures, diagnose incidents, or execute recovery actions.

## Features

- REST API built with FastAPI.
- PostgreSQL persistence using SQLAlchemy.
- UUID-based operation identifiers.
- Controlled operation state transitions.
- Request validation using Pydantic.
- Consistent JSON error responses.
- Structured application logging.
- Database schema migrations using Alembic.
- Automated tests using pytest.
- CI testing with GitHub Actions.
- Docker Compose development environment.
- Cloud deployment using Render and Neon.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| API framework | FastAPI |
| ASGI server | Uvicorn |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Validation and settings | Pydantic, pydantic-settings |
| Testing | pytest, HTTPX |
| Containerization | Docker, Docker Compose |
| CI | GitHub Actions |
| Database hosting | Neon |
| API hosting | Render |

## Architecture

```text
                 API Client
                     |
                     v
              FastAPI Application
                     |
          +----------+----------+
          |          |          |
          v          v          v
      Validation  State      Structured
      (Pydantic)  Logic      Logging
          |          |
          +----------+
                     |
                     v
              SQLAlchemy ORM
                     |
                     v
                PostgreSQL
            (operation records)


```

The application separates HTTP request handling, validation, state-transition rules, and database persistence.

## Operation Lifecycle

Each operation has one of four statuses:

| Current status | Allowed next status |
|---|---|
| `pending` | `running` |
| `running` | `succeeded`, `failed` |
| `succeeded` | None |
| `failed` | None |

Terminal states cannot be changed.

An attempt to perform an invalid transition returns HTTP `409 Conflict`.

## API Reference

Base URL (deployed):

`https://recovery-operations-api.onrender.com`

Interactive API documentation is available at `/docs`.

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/operations` | Create an operation |
| GET | `/operations` | List operations |
| GET | `/operations/{operation_id}` | Retrieve an operation |
| PATCH | `/operations/{operation_id}` | Update operation status |

### Create an operation

Request:

```http
POST /operations
Content-Type: application/json
```

```json
{
  "service_name": "payment-service",
  "failure_type": "health_check_failed"
}
```

Successful response: `201 Created`

```json
{
  "id": "1b001c1e-c39b-47cb-a4ed-296c8a48dd28",
  "service_name": "payment-service",
  "failure_type": "health_check_failed",
  "status": "pending",
  "created_at": "2026-11-06T12:00:00Z"
}
```

### Update operation status

Request:

```http
PATCH /operations/{operation_id}
Content-Type: application/json
```

```json
{
  "status": "running"
}
```

The requested status must follow the operation lifecycle rules.

### Error Responses

Errors use a consistent JSON structure.

Example: invalid state transition (`409 Conflict`).

```json
{
  "error": {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Transition from 'succeeded' to 'running' is not allowed"
  }
}
```

Supported error codes:

| HTTP status | Error code | Meaning |
|---|---|---|
| 404 | `OPERATION_NOT_FOUND` | Operation does not exist |
| 409 | `INVALID_STATE_TRANSITION` | Requested transition is not allowed |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 500 | `INTERNAL_SERVER_ERROR` | Internal or database error |

Validation errors include field-level details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "body.service_name",
        "message": "String should have at least 1 character",
        "type": "string_too_short"
      }
    ]
  }
}
```

## Local Development

### Prerequisites

- Python 3.13
- PostgreSQL 17, or Docker with Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/khaled-hoshan/recovery-operations-api.git
cd recovery-operations-api
```

### 2. Create a virtual environment

```bash
~/miniconda3/bin/python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg://recovery_app:local_dev_password@localhost:5432/recovery_operations
TEST_DATABASE_URL=postgresql+psycopg://recovery_app:local_dev_password@localhost:5432/recovery_operations_test
```

These variables configure the application database and the separate test database.

Do not commit `.env` or expose database credentials.

### 4. Prepare PostgreSQL

Connect to PostgreSQL as an administrative user, then create the application role and databases:

```sql
CREATE ROLE recovery_app WITH LOGIN PASSWORD 'local_dev_password';

CREATE DATABASE recovery_operations OWNER recovery_app;
CREATE DATABASE recovery_operations_test OWNER recovery_app;
```

The test database is separate so that automated tests do not modify application data.

### 5. Apply database migrations

```bash
python -m alembic upgrade head
```

### 6. Start the API

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

Interactive documentation:

`http://127.0.0.1:8000/docs`

## Running Tests

Tests use a separate PostgreSQL database configured through `TEST_DATABASE_URL`.

Run the complete test suite:

```bash
python -m pytest -v
```

The test setup applies Alembic migrations to the test database and uses transaction rollback to isolate individual tests.

The suite covers:

- Health checks.
- Operation creation and retrieval.
- Operation listing.
- Request validation.
- Valid and invalid state transitions.
- Terminal-state enforcement.
- Missing operation handling.
- Database error handling.
- Standardized error responses.

## Docker Compose

Docker Compose provides a containerized development environment with PostgreSQL and the API.

Compose uses `local_dev_password` as the default PostgreSQL password.
To override it, define `POSTGRES_PASSWORD` in the project-root `.env` file.

Build and start the services:

```bash
docker compose up --build
```

The Compose configuration:

1. Starts PostgreSQL.
2. Waits for the database health check.
3. Builds the API image.
4. Applies Alembic migrations.
5. Starts Uvicorn.

The API is available at:

`http://localhost:8000`

Stop the services:

```bash
docker compose down
```

To remove the PostgreSQL data volume as well:

```bash
docker compose down -v
```

**Warning:** Removing the volume deletes the local PostgreSQL data.

## CI/CD

### Continuous Integration

GitHub Actions runs the test suite on:

- Pushes to `main`.
- Pull requests targeting `main`.

The CI workflow:

1. Checks out the repository.
2. Sets up Python 3.13.
3. Starts a PostgreSQL 17 service.
4. Installs development dependencies.
5. Creates a separate test database.
6. Runs pytest.

### Database Migrations

Run this workflow after deploying a new database migration to the repository.
A separate manually triggered GitHub Actions workflow applies Alembic migrations to the production Neon database.

It reads the database connection string from the GitHub Actions secret:

`NEON_DATABASE_URL`

The database URL is not stored in the repository.

### Production Deployment

The deployed architecture uses:

- **Render:** Hosts the FastAPI application.
- **Neon:** Provides the managed PostgreSQL database.

Render configuration:

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required environment variable:

```text
DATABASE_URL
```

The production database schema is managed through Alembic migrations.

Deployed API:

https://recovery-operations-api.onrender.com

## Project Structure

```text
recovery-operations-api/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── neon-migrate.yml
├── alembic/
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   └── models.py
├── tests/
│   ├── conftest.py
│   └── test_main.py
├── .dockerignore
├── .gitignore
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Skills Demonstrated

- Python application development.
- REST API design.
- FastAPI request handling and validation.
- Relational database design and persistence.
- SQLAlchemy ORM.
- Database schema migrations.
- Unit and integration testing.
- Test database isolation.
- Structured logging and error handling.
- Docker containerization.
- CI/CD automation.
- Cloud application deployment.

## License

See [LICENSE](LICENSE).
