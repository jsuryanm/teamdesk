# TeamDesk

A helpdesk and ticketing system built with **FastAPI**, **PostgreSQL**, **Streamlit**, **Pydantic** and **Pydantic Logfire**, packaged with **Docker Compose** and managed with **uv**.

```
 Browser ──► Streamlit UI ──HTTP/JSON──► FastAPI (async) ──► services ──► SQLAlchemy (async) ──► PostgreSQL
 (:8501)       (frontend/)               (:8000)           (business rules)                      (:5432)
                    └────────────── traces & logs (Pydantic Logfire) ──────────────┘
```

## Features

* **Requesters** open tickets, comment, close their own tickets, and see only their own.
* **Agents** see every ticket; filter, full-text search, sort, assign, change status, and read the audit history.
* **Admins** also manage users and can delete tickets.
* **Dashboard** with live counts by status and priority and tickets created per day.
* Role-based access control, JWT authentication, Argon2 password hashing, and an audit log written in the same transaction as every change.
* Async request handling with independent queries executed in parallel for low latency.
* Request IDs and distributed traces from the UI click through the API to each SQL statement.

## Quick start

```bash
docker compose up --build
```

Open **http://localhost:8501** and sign in with `admin@teamdesk.dev` / `Password123!`.
API documentation: http://localhost:8000/docs

Step-by-step instructions for every setup option, plus how each component is configured, are in **[docs/SETUP.md](docs/SETUP.md)**.

## Development

Requires [Docker](https://www.docker.com/products/docker-desktop/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
make install        # uv sync for backend and frontend
make db             # start PostgreSQL only
make migrate seed   # create tables and demo data
make api            # API on :8000 with auto-reload   (second terminal: make ui)
make test-db test   # backend tests (needs a running database)
make test-ui lint   # frontend tests, ruff
```

Without `make`, the equivalent commands are in [docs/SETUP.md](docs/SETUP.md#path-b-python-on-your-machine-with-uv-for-development).

## Configuration

Every setting has a working default; copy `.env.example` to `.env` only to change something.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local PostgreSQL | database connection (set automatically in Docker) |
| `SECRET_KEY` | insecure dev key | signs JWTs; **required** to be set when `ENVIRONMENT` is `staging` or `production` |
| `ENVIRONMENT` | `local` | `local`, `test`, `staging`, `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | login lifetime |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `5`, `10` | API connection pool |
| `SEED_DEMO_DATA` | `true` | load demo users and tickets on first container start |
| `LOGFIRE_TOKEN` | *(unset)* | send telemetry to Logfire; logs go to the console without it |

## Project layout

```
teamdesk/
├── docker-compose.yml        # db + backend + frontend (+ jupyter, adminer via profiles)
├── .env.example
├── Makefile
├── backend/                  # FastAPI service
│   ├── pyproject.toml  uv.lock
│   ├── app/
│   │   ├── api/              #   routes and dependencies (thin HTTP layer)
│   │   ├── services/         #   business rules
│   │   ├── schemas/          #   Pydantic request/response models
│   │   ├── models/           #   SQLAlchemy tables
│   │   ├── core/             #   settings, security, observability, exceptions, concurrency helpers
│   │   ├── db/               #   async engine, session, base class
│   │   ├── main.py           #   application factory
│   │   └── seed.py           #   demo data
│   ├── alembic/              #   database migrations
│   ├── tests/                #   pytest suite (real PostgreSQL)
│   └── Dockerfile
├── frontend/                 # Streamlit service
│   ├── pyproject.toml  uv.lock
│   ├── app.py  views/  api_client.py  state.py  models.py
│   ├── tests/                #   headless UI tests
│   └── Dockerfile
├── notebooks/                # interactive walkthroughs (outputs included)
├── docs/                     # documentation
└── .github/workflows/ci.yml  # lint, migrations, tests, image build
```

## Design notes

| Choice | Reason |
|---|---|
| Layers: routes → services → models | business rules are testable without HTTP; routes stay thin |
| Async SQLAlchemy + `asyncio.TaskGroup` fan-out | one process serves many requests; independent queries overlap |
| Separate Pydantic schemas and ORM models | the API contract can change independently of the tables |
| Alembic migrations, checked in CI (`alembic check`) | schema changes are versioned, reviewable and reversible |
| `404` instead of `403` for other users' tickets | does not reveal that a ticket exists |
| Separate UI and API projects sharing only HTTP | independent dependencies and deployment |
| uv with a committed `uv.lock` | identical dependency versions on laptops, CI and in Docker |
| Logfire (OpenTelemetry) | a single trace across UI, API and SQL |
| Tests against real PostgreSQL | JSONB, generated columns and GIN indexes behave as in production |

## Testing

```bash
cd backend  && uv run pytest -q      # 38 tests (async, real PostgreSQL)
cd frontend && uv run pytest -q      # 6 tests (UI via Streamlit AppTest, parallel client)
```
Continuous integration (`.github/workflows/ci.yml`) runs lint, migrations (`upgrade` and `check`), both test suites, and builds the Docker images.

## Documentation

| | |
|---|---|
| Getting started | [Setup guide](docs/SETUP.md) · [Build order](docs/BUILD-ORDER.md) · [Architecture](docs/01-architecture.md) |
| Components | [Pydantic](docs/02-pydantic.md) · [PostgreSQL](docs/03-postgresql.md) · [SQLAlchemy & Alembic](docs/04-sqlalchemy-alembic.md) · [**Alembic migrations**](docs/ALEMBIC.md) · [FastAPI](docs/05-fastapi.md) · [Auth & security](docs/06-auth-and-security.md) · [Logfire](docs/07-logfire-observability.md) · [Streamlit](docs/08-streamlit.md) · [Docker & Compose](docs/09-docker-compose.md) · [Testing](docs/10-testing.md) · [Async & parallelism](docs/14-async-and-parallelism.md) |
| Reference | [Enterprise practices](docs/11-enterprise-best-practices.md) · [Cheat sheet & glossary](docs/12-cheatsheet-and-glossary.md) · [Exercises](docs/13-exercises.md) · [Study plan](docs/00-learning-path.md) |

Notebooks in [`notebooks/`](notebooks/) walk through each technology interactively: Pydantic, PostgreSQL, SQLAlchemy and Alembic, FastAPI, authentication, Logfire, Streamlit and testing, Docker Compose, and async programming.

## Before deploying to production

The defaults favour a frictionless local start. Change these first:

* disable demo data (`SEED_DEMO_DATA=false`) and set a random `SECRET_KEY` (the app refuses to start in `staging`/`production` without one);
* do not publish the database port; use a managed PostgreSQL with backups;
* run `alembic upgrade head` as a one-off release job instead of from every container start;
* serve over HTTPS and set `CORS_ORIGINS` to the real UI origin.

See [docs/11-enterprise-best-practices.md](docs/11-enterprise-best-practices.md) for the full checklist.
# teamdesk
