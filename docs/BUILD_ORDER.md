# Build Order: which file to write first

Write the project **bottom-up**: start with the files that depend on nothing, and finish with the files that depend on everything. After every step there is a **checkpoint**, a command that proves the step works before you move on. If a checkpoint fails, fix it now; never build on top of a broken layer.

```
config ─► db ─► models ─► migrations ─► schemas ─► services ─► routes ─► main ─► tests ─► docker ─► frontend
  (nothing        (needs db)  (needs models)  (needs models)  (needs all    (needs all above)
   depends on)                                                 of these)
```

**Rule of thumb:** if file A imports file B, write B first.

---

## Step 0: Skeleton and tools (15 min)

| Create | What goes in it |
|---|---|
| Folders | `backend/app/{core,db,models,schemas,services,api/routes}`, `backend/tests`, `frontend/views`, `docs`, `notebooks` (or run `bash create_template.sh`) |
| `.gitignore`, `.env.example` | what git must ignore; every setting with a safe default |
| `backend/pyproject.toml` (+ `uv.lock`), `frontend/pyproject.toml` | dependencies, tool settings; `uv lock` writes the lock file |
| `docker-compose.yml` (**only the `db` service for now**) | PostgreSQL 16 with a healthcheck and a volume |

```bash
cd backend && uv sync                # creates backend/.venv from pyproject.toml / uv.lock
docker compose up -d db              # (from the project root)
# add a library later with:  uv add <name>   (dev-only: uv add --dev <name>)
```
✅ **Checkpoint:** `docker compose ps` shows `db` as **healthy**.

---

## Step 1: Configuration (`core/config.py`)

Everything else reads settings from here, so it comes first.
* A `Settings` class (pydantic-settings) with `database_url`, `secret_key`, `environment`, pool sizes, CORS origins, optional `logfire_token`.
* A validator that refuses the default secret key in `staging`/`production`.
* `get_settings()` with `@lru_cache`.

✅ **Checkpoint:** `uv run python -c "from app.core.config import get_settings; print(get_settings().environment)"` prints `local`.
Concepts: [02-pydantic.md](02-pydantic.md)

## Step 2: Errors and security helpers (`core/exceptions.py`, `core/security.py`)

* `exceptions.py`: `DomainError` and its subclasses (400, 401, 403, 404, 409). Plain Python, no FastAPI.
* `security.py`: `hash_password`, `verify_password`, `DUMMY_HASH`, `create_access_token`, `decode_access_token`.

✅ **Checkpoint:** hash a password, verify it, create a token and decode it in a Python shell.
Concepts: [06-auth-and-security.md](06-auth-and-security.md)

## Step 3: Database plumbing (`db/base.py`, `db/session.py`)

* `base.py`: `Base`, the constraint **naming convention**, `TimestampMixin` (`created_at`, `updated_at`).
* `session.py`: the **async** engine, `async_sessionmaker` (`expire_on_commit=False` is required), and the `get_db` dependency.

✅ **Checkpoint:** run this from `backend/`; it should print `1`:
```bash
uv run python -c "
import asyncio
from sqlalchemy import text
from app.db.session import engine
async def main():
    async with engine.connect() as c:
        print((await c.execute(text('select 1'))).scalar())
    await engine.dispose()
asyncio.run(main())"
```
Concepts: [04-sqlalchemy-alembic.md](04-sqlalchemy-alembic.md), [14-async-and-parallelism.md](14-async-and-parallelism.md)

## Step 4: Models (`models/enums.py`, `user.py`, `ticket.py`, `audit.py`, `__init__.py`)

Order inside the folder matters:
1. `enums.py`: `Role`, `TicketStatus`, `TicketPriority`.
2. `user.py`: `User`.
3. `ticket.py`: `ticket_tags` table, `Tag`, `Ticket` (with the generated `search_vector` and indexes), `Comment`.
4. `audit.py`: `AuditLog` (JSONB `details`).
5. `__init__.py`: import every model, so Alembic can see them.

✅ **Checkpoint:** `uv run python -c "import app.models; from app.db.base import Base; print(sorted(Base.metadata.tables))"` lists 6 tables.
> Async rule for models: relationships you always need should use `lazy="selectin"` (like `Ticket.tags`) or be loaded explicitly with `joinedload`. A lazy load cannot `await`.

## Step 5: Migrations (Alembic)

Create the files in this order:
1. `alembic.ini` (mostly defaults)
2. `alembic/env.py` (connects Alembic to your settings and `Base.metadata`)
3. `alembic/script.py.mako` (template for new migration files)
4. Generate the first migration **from your models**; don't write it by hand.

```bash
cd backend
uv run alembic revision --autogenerate -m "initial schema"
# open the new file in alembic/versions/ and READ it
uv run alembic upgrade head
uv run alembic check
```
✅ **Checkpoint:** `alembic check` says *No new upgrade operations detected*, and `docker compose exec db psql -U teamdesk -d teamdesk -c '\dt'` shows your tables.
Full guide: [ALEMBIC.md](ALEMBIC.md)

## Step 6: Schemas (`schemas/common.py`, `user.py`, `ticket.py`)

* `common.py`: `Page[T]` (generic pagination envelope), `ErrorResponse`.
* `user.py`: `UserCreate` (**no `role` field**), `UserRead`, `Token`, admin variants.
* `ticket.py`: `TicketCreate`, `TicketUpdate`, `TicketFilters`, `TicketSummary`, `TicketRead`, comment and stats models.

✅ **Checkpoint:** write `tests/test_schemas.py` now (pure Python, no database) and run `pytest tests/test_schemas.py`.

## Step 7: Services (the business rules)

1. `core/concurrency.py`: the `gather_all` helper (used by services).
2. `services/audit.py`: `record()`, the smallest service.
3. `services/users.py`: create, authenticate, list, update. (Argon2 runs in `asyncio.to_thread`.)
4. `services/tickets.py`: visibility, state machine, filters, comments, stats (with parallel queries).

Write `users.py` before `tickets.py`: tickets need users.

✅ **Checkpoint:** call a service from a Python shell (see notebook 03 / 05) or go straight to the next steps and test through the API.

## Step 8: Observability (`core/observability.py`)

`setup_observability()` and `instrument_app()`. Written **before the routes** so that every route you build from here on is traced.

✅ **Checkpoint:** later, in Step 10, you will see spans in the terminal.
Concepts: [07-logfire-observability.md](07-logfire-observability.md)

## Step 9: API layer (`api/`)

1. `api/deps.py`: `DbSession`, `CurrentUser`, `require_roles`, `StaffUser`, `AdminUser`.
2. `api/routes/health.py`: simplest route; use it to prove the wiring.
3. `api/routes/auth.py`: register + login.
4. `api/routes/users.py`
5. `api/routes/tickets.py`: (`/stats` **before** `/{ticket_id}`).
6. `api/router.py`: combines routers under `/api/v1`.

## Step 10: Application entry point (`main.py`)

`create_app()`: lifespan, CORS, request-id middleware, the `DomainError` handler, routers.

```bash
cd backend && uv run uvicorn app.main:app --reload
```
✅ **Checkpoint:** open http://localhost:8000/docs, call `GET /health/ready` (expect `database: up`), register a user, **Authorize**, call `GET /api/v1/users/me`. Check the terminal for Logfire spans.

## Step 11: Seed data (`seed.py`)

Demo users and tickets so every screen has something to show. Make it **idempotent** (running twice changes nothing).

✅ **Checkpoint:** `uv run python -m app.seed` prints *Seeded 5 users and 40 tickets*; the second run prints *Seed skipped*.

## Step 12: Backend tests

1. `tests/conftest.py`: fixtures (clean tables, async client, `make_user`, `auth`, `create`).
2. `test_health.py`, then `test_auth.py`, then `test_tickets.py`, then `test_concurrency.py`.

```bash
cd backend && uv run pytest -q
```
✅ **Checkpoint:** all green. Add a failing test **first** for any bug you find from now on.
Concepts: [10-testing.md](10-testing.md)

## Step 13: Containerize the backend

1. `backend/.dockerignore`
2. `backend/Dockerfile` (multi-stage, non-root, healthcheck)
3. `backend/docker-entrypoint.sh` (migrate → optional seed → `exec uvicorn`)
4. Add the `backend` service to `docker-compose.yml` with `depends_on: db: condition: service_healthy`.

```bash
docker compose up --build -d db backend
curl localhost:8000/health/ready
```
✅ **Checkpoint:** `docker compose ps` shows `backend` **healthy**.
Concepts: [09-docker-compose.md](09-docker-compose.md)

## Step 14: Frontend (Streamlit)

Order inside `frontend/`:
1. `config.py`: `API_URL` setting.
2. `models.py`: Pydantic models for API responses.
3. `api_client.py`: the typed HTTP client (the only file that talks HTTP).
4. `observability.py`: Logfire for the UI.
5. `state.py`: login/logout, `api_errors()`.
6. `views/login.py`, then `dashboard.py`, `tickets.py`, `new_ticket.py`, `admin_users.py`.
7. `ticket_detail.py`
8. `app.py`: navigation and the login gate. Last, because it imports everything.

```bash
cd frontend && uv sync && uv run streamlit run app.py
```
✅ **Checkpoint:** log in as `admin@teamdesk.dev`, open the dashboard and a ticket.
Then write `tests/conftest.py` + `tests/test_app.py` (fake client + `AppTest`).
Concepts: [08-streamlit.md](08-streamlit.md)

## Step 15: Finish the stack

1. `frontend/.dockerignore`, `frontend/Dockerfile`, `frontend/.streamlit/config.toml`
2. Add `frontend` (and optional `jupyter`, `adminer`) to `docker-compose.yml`.
3. `Makefile`: shortcuts for what you now type often.
4. `.github/workflows/ci.yml`: lint, migrations, tests, image build.

```bash
docker compose down -v && docker compose up --build
```
✅ **Checkpoint:** from a clean slate, the UI is at http://localhost:8501 and you can log in.

## Step 16: Documentation and notebooks

Write these last, while everything is fresh: `README.md`, `docs/SETUP.md`, then the notebooks. Explaining the code is the best test that you understand it.

---

## Summary table

| # | Write | Depends on | Verify with |
|---|---|---|---|
| 0 | skeleton, compose `db` | none | `docker compose ps` |
| 1 | `core/config.py` | none | print a setting |
| 2 | `core/exceptions.py`, `security.py` | config | hash/verify/token |
| 3 | `db/base.py`, `session.py` | config | `select 1` |
| 4 | `models/*` | db | list tables |
| 5 | `alembic/*` + first migration | models | `alembic check` |
| 6 | `schemas/*` | models (enums) | `test_schemas.py` |
| 7 | `core/concurrency.py`, `services/*` | models, schemas, security | shell / API |
| 8 | `core/observability.py` | config | spans in terminal |
| 9 | `api/*` | services, schemas | `/docs` |
| 10 | `main.py` | api, observability | `/health/ready` |
| 11 | `seed.py` | services | seed twice |
| 12 | `tests/*` | everything backend | `pytest` |
| 13 | backend Docker | backend | `compose ps` healthy |
| 14 | `frontend/*` | running API | log in via UI |
| 15 | frontend Docker, Makefile, CI | all | clean `up --build` |
| 16 | docs, notebooks | all | none |

## Habits that make this order work
* **Commit after every checkpoint** (`git commit -m "step 5: initial migration"`). A broken step is then one `git diff` away.
* **Keep the previous layer's tests green.** If step 7 breaks step 6's tests, you changed a contract; stop and decide on purpose.
* **Resist jumping ahead** to the UI. A UI on top of an untested API hides bugs behind widgets.
* **Add one feature at a time through all layers** (model → migration → schema → service → route → test → UI) once the base exists. [13-exercises.md](13-exercises.md) practices exactly this.
