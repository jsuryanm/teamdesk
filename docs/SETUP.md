# Setup Guide

This guide gets TeamDesk running, then explains **how each part is set up and how to check it**: the project itself, uv, Pydantic settings, Docker, PostgreSQL, Alembic and Logfire.

| I want to... | Use | Time | Needs |
|---|---|---|---|
| **Run the app** with the least effort | **Path A: Docker only** | ~5 min | Docker |
| **Edit code**, run tests, debug | **Path B: uv + Docker database** | ~15 min | Docker + uv |
| **Open the notebooks** | **Path C: Notebooks** | ~10 min | Docker + uv *or* Docker only |

Pick **one** path. You can switch later. Then read [Part 2](#part-2-how-each-part-is-set-up) when you want to understand what you just started.

---

## Part 1: Get it running

### 0. What you need installed

| Tool | Needed for | Check it | Get it |
|---|---|---|---|
| **Docker** with Compose v2 | all paths | `docker --version` and `docker compose version` | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) · Docker Engine + Compose plugin (Linux) |
| **uv** (Python package manager) | Paths B and C | `uv --version` | see below |
| `make` *(optional)* | shortcuts | `make --version` | Mac/Linux have it. On Windows skip it: every `make` command has a plain command next to it |
| A code editor | Path B | | [VS Code](https://code.visualstudio.com/) |

**Install uv** (one command; it also manages Python itself, so you do not need to install Python separately):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# or, if you prefer:  brew install uv     /     pip install uv
```
Close and reopen the terminal, then run `uv --version`.

> **Windows:** run the backend in Docker (Path A) or inside **WSL**. The async PostgreSQL driver needs a selector event loop that native Windows Python does not use by default. The Docker path works everywhere.

**Start Docker Desktop first** (it must say "running"). Then open a terminal in the project folder:

```bash
cd teamdesk
```

---

### Path A: Docker only (easiest)

**1. Start everything**

```bash
docker compose up --build
```
The first run downloads images and builds the services: **3-6 minutes**. Later runs take seconds. You do **not** need to create a config file: every setting has a working default.

**2. Wait for** `Application startup complete` (backend) and `You can now view your Streamlit app` (frontend).

**3. Open the app**

| What | Address |
|---|---|
| **TeamDesk UI** | http://localhost:8501 |
| **API documentation** (try requests in the browser) | http://localhost:8000/docs |
| API health check | http://localhost:8000/health/ready |

**4. Sign in** with a demo account (created automatically on first start):

| Role | Email | Password | Can do |
|---|---|---|---|
| Admin | `admin@teamdesk.dev` | `Password123!` | everything, manage users |
| Agent | `agent@teamdesk.dev` | `Password123!` | see and work all tickets |
| Requester | `user@teamdesk.dev` | `Password123!` | see only their own tickets |

> Demo passwords are public. Turn demo data off with `SEED_DEMO_DATA=false` in `.env`.

**5. Stop it**

```bash
# Ctrl+C in the terminal, then:
docker compose down        # stops containers, KEEPS your data
docker compose down -v     # stops containers AND DELETES the database (fresh start)
```
Run in the background instead: `docker compose up --build -d` (or `make up`), then `docker compose logs -f`.

**What just happened?**
1. Docker started **PostgreSQL** and waited until it reported *healthy*.
2. The **backend** container applied the database migrations (`alembic upgrade head`), loaded demo data, and started FastAPI.
3. The **frontend** container started Streamlit and pointed it at `http://backend:8000`.

---

### Path B: Python on your machine with uv (for development)

Python runs on **your computer** (fast reload, easy debugging); only the **database** runs in Docker.

**1. Install the dependencies.** uv creates a virtual environment in each project folder and installs exactly what `uv.lock` says:

```bash
cd backend  && uv sync && cd ..       # creates backend/.venv
cd frontend && uv sync && cd ..       # creates frontend/.venv
# shortcut for both: make install
```
You never need to "activate" anything: `uv run <command>` always uses the right environment.

**2. Create your config file** (optional; defaults also work)

```bash
cp .env.example .env                  # Windows: copy .env.example .env
```

**3. Start only the database**

```bash
docker compose up -d db               # shortcut: make db
```

**4. Create the tables and demo data**

```bash
cd backend
uv run alembic upgrade head           # creates all tables           (make migrate)
uv run python -m app.seed             # demo users + 40 tickets      (make seed)
cd ..
```

**5. Run the API and the UI** in two terminals:

```bash
# Terminal 1: API with auto-reload on code changes      (make api)
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Streamlit UI                              (make ui)
cd frontend && uv run streamlit run app.py
```
Open http://localhost:8501 and sign in as above.

**6. Run the tests** (one-time: create the separate test database)

```bash
docker compose exec db psql -U teamdesk -d postgres -c "CREATE DATABASE teamdesk_test OWNER teamdesk;"    # make test-db

cd backend  && uv run pytest -q       # expect: 38 passed    (make test)
cd frontend && uv run pytest -q       # expect: 6 passed     (make test-ui)
cd backend  && uv run ruff check .    # expect: All checks passed!   (make lint)
```

---

### Path C: Just the notebooks

**Option 1: on your machine**
```bash
docker compose up -d db                                         # needed by notebooks 02, 03, 08, 09
cp .env.example .env
cd backend
uv run alembic upgrade head && uv run python -m app.seed
uv run --group notebooks jupyter lab --notebook-dir=../notebooks      # make lab
```
`--group notebooks` installs the extra notebook tools (JupyterLab, pandas, Streamlit for notebook 07) on first use.

**Option 2: everything in Docker (no Python or uv needed)**
```bash
docker compose --profile learn up --build
```
Open **http://localhost:8888** and enter the token **`teamdesk`**.

| # | Notebook | Needs running |
|---|---|---|
| 01 | Pydantic | nothing |
| 02 | PostgreSQL & SQL | database |
| 03 | SQLAlchemy & Alembic | database |
| 04 | FastAPI | nothing |
| 05 | Auth, JWT & RBAC | nothing |
| 06 | Logfire | nothing |
| 07 | Streamlit & testing | nothing |
| 08 | Docker & end-to-end | **the full app** (Path A, or Path B with the API running) |
| 09 | Async & parallelism | database with demo data |

Run cells with **Shift+Enter**, in order. Notebooks 02-03 create a throw-away schema and clean up after themselves.

---

### Check that it works (any path)

```bash
curl http://localhost:8000/health/ready
# expect: {"status":"ok","database":"up", ...}
```
* Open http://localhost:8501, sign in as `admin@teamdesk.dev`: the **Dashboard** shows numbers and charts.
* Open http://localhost:8000/docs, click **Authorize**, log in, run `GET /api/v1/tickets`.

---

## Part 2: How each part is set up

### 2.1 The project and its configuration

```
teamdesk/
├── docker-compose.yml     starts db + backend + frontend (+ optional jupyter, adminer)
├── .env.example           every setting, with safe defaults (copy to .env to change)
├── Makefile               shortcuts: make up / test / migrate / seed ...
├── backend/               FastAPI service   (own pyproject.toml + uv.lock + Dockerfile)
├── frontend/              Streamlit service (own pyproject.toml + uv.lock + Dockerfile)
├── notebooks/  docs/      interactive walkthroughs and documentation
└── .github/workflows/     CI
```
The backend and frontend are **two independent Python projects**. They only share an HTTP contract, so each has its own dependencies, lock file and image.

**Where settings come from** (first match wins):

| Priority | Source | Example |
|---|---|---|
| 1 | environment variables (shell, or `environment:` in compose) | `ENVIRONMENT=production` |
| 2 | the `.env` file | `SECRET_KEY=...` |
| 3 | defaults written in the code (`backend/app/core/config.py`) | `ACCESS_TOKEN_EXPIRE_MINUTES = 60` |

`.env` is read from the project root (or from `backend/`). Because everything has a default, **no `.env` is required**.
In Docker, compose sets `DATABASE_URL` and `API_URL` itself (with the container hostnames `db` and `backend`), so the `localhost` values in your `.env` never break the containers.

| Setting | Default | Meaning |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `teamdesk` | database credentials (Docker) |
| `DB_PORT` | `5432` | database port on **your computer**. Change it if 5432 is taken (also update `DATABASE_URL`) |
| `DATABASE_URL` | `postgresql+psycopg://teamdesk:teamdesk@localhost:5432/teamdesk` | used when Python runs on your machine |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `10` | connection pool of the API (see [14-async-and-parallelism.md](14-async-and-parallelism.md)) |
| `ENVIRONMENT` | `local` | `local`, `test`, `staging`, `production` |
| `SECRET_KEY` | insecure dev key | signs login tokens. **Must be changed** outside local use |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | how long a login lasts |
| `SEED_DEMO_DATA` | `true` | load demo users/tickets on first container start |
| `API_URL` | `http://localhost:8000` | where the UI finds the API |
| `LOGFIRE_TOKEN` | *(empty)* | send telemetry to Logfire cloud |

Generate a real secret key: `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

### 2.2 uv (Python packages and environments)

**What it is:** one fast tool that replaces `pip`, `venv`, `pip-tools` and `pyenv`. It reads the dependencies from **`pyproject.toml`** and records the exact resolved versions in **`uv.lock`**.

| File | Purpose | Edit it? |
|---|---|---|
| `backend/pyproject.toml` | the dependency **wishes** (`fastapi>=0.165,<1`), tool settings (pytest, ruff) | yes (or via `uv add`) |
| `backend/uv.lock` | the exact versions of **all** packages (transitive ones too) | **no**, uv writes it. Commit it |
| `backend/.venv/` | the virtual environment uv creates | no, not committed |

`pyproject.toml` has three kinds of dependencies:

| Group | Installed by | Contains |
|---|---|---|
| `dependencies` | always | FastAPI, SQLAlchemy, Pydantic, Logfire ... (what production needs) |
| `dev` (default) | `uv sync` | pytest, pytest-asyncio, httpx, ruff |
| `notebooks` | `uv sync --group notebooks` | JupyterLab, pandas, Streamlit |

**Commands you will use**

| Task | Command |
|---|---|
| Install everything from the lock file | `uv sync` (add `--locked` to fail if the lock is out of date) |
| Run something in the project environment | `uv run pytest -q` · `uv run alembic upgrade head` · `uv run uvicorn ...` |
| Add a library | `uv add httpx` · dev-only: `uv add --dev pytest-cov` |
| Remove a library | `uv remove httpx` |
| Upgrade everything within the allowed ranges | `uv lock --upgrade` then `uv sync` |
| Upgrade one library | `uv lock --upgrade-package fastapi` |
| See what is installed | `uv pip list` |

**Why a lock file?** `pyproject.toml` says *"FastAPI 0.165 or newer, below 1.0"*; the lock says *"exactly 0.165.0, and the exact version of every other package"*. Everyone (laptops, CI, Docker) installs the **same** set, so "works on my machine" bugs disappear.

**A real lesson in this project:** `sqlalchemy>=2.0.58,<2.1`. SQLAlchemy 2.1 is newer, but Logfire's SQLAlchemy instrumentation did not support it when this project was built. The ceiling is written into `pyproject.toml` with a comment. Whenever you upgrade, run the tests first.

**In Docker:** each Dockerfile copies `pyproject.toml` + `uv.lock` first and runs `uv sync --locked --no-dev`. That layer is cached until the dependencies change, and `--locked` makes the build fail if someone forgot to update the lock.

---

### 2.3 Pydantic (validation and settings)

Pydantic is used in three places. Knowing which one is failing tells you where to look:

| Where | File | What it validates | Failure looks like |
|---|---|---|---|
| **Settings** (start-up) | `backend/app/core/config.py` | environment variables / `.env` | the app refuses to start with a `ValidationError` |
| **API input** | `backend/app/schemas/` | request bodies and query strings | HTTP `422` with the field names |
| **API output** | `backend/app/schemas/` + `frontend/models.py` | what the API returns / what the UI accepts | filtered response / loud error in the UI |

**See the effective settings** (secrets are masked):

```bash
cd backend && uv run python -c "from app.core.config import get_settings; print(get_settings())"
# ... db_pool_size=5 db_max_overflow=10 secret_key=SecretStr('**********') ... logfire_token=None
```

**Watch start-up validation protect you** (try these; they are safe):

```bash
cd backend
DB_POOL_SIZE=0 uv run python -c "from app.core.config import get_settings; get_settings()"
# ValidationError: db_pool_size  Input should be greater than or equal to 1

ENVIRONMENT=production uv run python -c "from app.core.config import get_settings; get_settings()"
# Value error, SECRET_KEY must be set to a random value (>= 32 chars) outside local/test
```
The second one is deliberate: **production can never start with the public development key.** (On Windows PowerShell set the variable first: `$env:ENVIRONMENT="production"`.)

**See API validation** at http://localhost:8000/docs: call `POST /api/v1/tickets` with `{"title": "x", "description": ""}` and read the `422` response.

More: [02-pydantic.md](02-pydantic.md), notebook `01_pydantic_foundations`.

---

### 2.4 Docker and Docker Compose

**The services**

| Service | Image / build | Port | Healthy when | Starts |
|---|---|---|---|---|
| `db` | `postgres:16-alpine` | `5432` | `pg_isready` succeeds | always |
| `backend` | built from `backend/Dockerfile` | `8000` | `GET /health/live` | after `db` is healthy |
| `frontend` | built from `frontend/Dockerfile` | `8501` | Streamlit `/_stcore/health` | after `backend` is healthy |
| `jupyter` | `docker/jupyter.Dockerfile` | `8888` | | only with `--profile learn` |
| `adminer` | `adminer` | `8080` | | only with `--profile tools` |

**Start-up order** (`depends_on` with `condition: service_healthy`): `db` healthy → `backend` (migrate → seed → serve) → `frontend`. Without the health condition, the backend could start before PostgreSQL is ready and crash.

**Containers talk by service name.** Inside Docker `localhost` means *the container itself*. The backend reaches the database at `db:5432`, the UI reaches the API at `http://backend:8000`.

**Data survives** in the named volume `pgdata`. `docker compose down` keeps it; `down -v` deletes it.

**Commands you will use**

```bash
docker compose up --build -d           # build and start in the background          (make up)
docker compose ps                      # status and health of every service
docker compose logs -f backend         # follow one service's logs                  (make logs)
docker compose exec db psql -U teamdesk -d teamdesk    # a shell inside a container (make psql)
docker compose restart backend
docker compose --profile learn up --build -d           # + JupyterLab on :8888      (make learn)
docker compose --profile tools up -d                   # + Adminer (DB web UI) :8080 (make tools)
docker compose down                    # stop, keep data                            (make down)
docker compose down -v                 # stop and delete the database              (make reset)
```

**Code change not showing?** Rebuild: `docker compose up --build`. **Config change?** `docker compose up -d` recreates the affected containers.

**The images** use **uv** to install dependencies in a build stage and copy only the finished virtual environment into a slim runtime image that runs as a **non-root user** with a **health check**. Details: [09-docker-compose.md](09-docker-compose.md).

---

### 2.5 PostgreSQL

**Connection details** (defaults)

| | Value |
|---|---|
| Host (from your computer) | `localhost` |
| Host (from another container) | `db` |
| Port | `5432` (`DB_PORT` to change) |
| User / password / database | `teamdesk` / `teamdesk` / `teamdesk` |
| Test database (used by pytest) | `teamdesk_test` (create it once, see Path B step 6) |
| Python URL | `postgresql+psycopg://teamdesk:teamdesk@localhost:5432/teamdesk` |

The URL has the form `driver://user:password@host:port/database`. `+psycopg` selects the **psycopg 3** driver, which serves both the async API and the sync Alembic.

**Three ways to look inside**

```bash
# 1. psql inside the container (no installation needed)           (make psql)
docker compose exec db psql -U teamdesk -d teamdesk
#   \dt  list tables      \d tickets  describe a table      \di  list indexes      \q  quit

# 2. Adminer in the browser:  docker compose --profile tools up -d  → http://localhost:8080
#    System: PostgreSQL · Server: db · Username/Password/Database: teamdesk

# 3. Any GUI (DBeaver, TablePlus, pgAdmin): host localhost, port 5432, credentials above
```

**Useful queries**

```sql
SELECT status, count(*) FROM tickets GROUP BY status;
SELECT version_num FROM alembic_version;                 -- which migration the database is at
SELECT title FROM tickets WHERE search_vector @@ plainto_tsquery('english', 'printer');
```

**Backup, restore, reset**

```bash
docker compose exec -T db pg_dump -U teamdesk teamdesk > backup.sql          # backup
docker compose exec -T db psql -U teamdesk -d teamdesk < backup.sql          # restore into an empty database
docker compose down -v && docker compose up --build                          # throw everything away and start fresh
```

**Port 5432 already in use** (a local PostgreSQL is running)? Set `DB_PORT=5433` in `.env`, update the port in `DATABASE_URL`, then `docker compose up -d db`.

More: [03-postgresql.md](03-postgresql.md), notebook `02_postgres_sql_fundamentals`.

---

### 2.6 Alembic (database migrations)

Alembic creates and changes the tables. **You never create tables by hand.**

| When | What happens |
|---|---|
| Docker (Path A) | the backend container runs `alembic upgrade head` before starting the API |
| Path B | you run `uv run alembic upgrade head` once (and after pulling new migrations) |
| You change a model | `uv run alembic revision --autogenerate -m "describe change"`, **read the new file**, then `upgrade head` |

```bash
cd backend
uv run alembic current        # which migration is this database at?     → 0001 (head)
uv run alembic upgrade head   # apply everything pending
uv run alembic check          # do the models and the database agree?    → No new upgrade operations detected.
```

Alembic is explained from zero in its own guide: **[ALEMBIC.md](ALEMBIC.md)**: how it works, every file, the daily workflow, renames, data migrations, team rules and troubleshooting.

---

### 2.7 Logfire (logs and traces)

**What you get:** structured logs plus **traces**: one request shown as a tree (UI click → API request → each SQL query).

Two modes, same code:

| Mode | Setup | Where you see data |
|---|---|---|
| **Console** (default) | nothing | the terminal / `docker compose logs -f backend` |
| **Logfire cloud** (optional) | a free token | the Logfire web dashboard, plus the console |

**Try it now (console):** sign in, click around, then run `docker compose logs backend` (or look at the terminal running uvicorn). You will see lines for each request, SQL statement, and the span `stats: 4 queries in parallel` with four `SELECT` lines inside it.

**Turn on the cloud dashboard**
1. Create a free account at https://logfire.pydantic.dev and create a project.
2. Project → **Settings → Write tokens** → create a token.
3. Put `LOGFIRE_TOKEN=<your token>` in `.env`, then restart: `docker compose up -d` (Path B: restart the two processes).
4. Use the app, then open the project's **Live** view.

**What is configured** (`backend/app/core/observability.py`, `frontend/observability.py`)

| Setting | Why |
|---|---|
| `send_to_logfire="if-token-present"` | no token = console only; the app never fails because of telemetry |
| service names `teamdesk-api` and `teamdesk-ui` | tell the two services apart |
| `distributed_tracing=True` + `instrument_httpx()` | the UI's call and the API's work join **one** trace |
| `instrument_sqlalchemy`, `instrument_fastapi`, `instrument_pydantic(record="failure")` | spans for SQL and requests, logs for validation failures only |
| `excluded_urls="/health"` | health probes don't flood the traces |
| default **scrubbing** | values of keys like `password`, `token`, `secret` are masked |

**Request IDs:** every response has an `X-Request-ID` header (and error responses contain `request_id`). Search for it in the logs to see everything that request did.

More: [07-logfire-observability.md](07-logfire-observability.md), notebook `06_logfire_observability`.

---

## Common problems

| Problem | Fix |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop and wait until it says "running" |
| `port is already allocated` / `address already in use` | Another program uses that port. Stop it, or set `DB_PORT=5433` in `.env`. For 8000 / 8501 change the left number in `docker-compose.yml` (e.g. `"8001:8000"`) |
| Login says *Cannot reach the API* | Backend not ready: `docker compose logs backend`. Path B: is the API terminal running? |
| `connection refused` to the database (Path B) | `docker compose up -d db`, then `docker compose ps` should show `healthy` |
| `relation "users" does not exist` | Tables not created: `uv run alembic upgrade head` in `backend/` |
| `uv: command not found` | Install uv (section 0) and reopen the terminal |
| `The lockfile ... needs to be updated` (`--locked`) | `pyproject.toml` changed without updating the lock: run `uv lock` |
| `ModuleNotFoundError` | Run through uv: `uv run <command>` (or `uv sync` first) |
| Pytest: `database "teamdesk_test" does not exist` | Create it (Path B step 6) |
| Pytest hangs or errors about the event loop | Run from `backend/` with `uv run pytest` so `pyproject.toml` (async settings) is used |
| I changed code but Docker shows the old version | `docker compose up --build` |
| I want a completely fresh start | `docker compose down -v` then `docker compose up --build` |
| Notebook 08 says *API not reachable* | Start the full app first (Path A), then re-run from that cell |
| `MissingGreenlet` while editing backend code | You touched a relationship that wasn't loaded: see [14-async-and-parallelism.md](14-async-and-parallelism.md) |

---

## Clean up

```bash
docker compose down -v          # remove containers and the database volume
docker image prune              # optional: free disk space used by old images
rm -rf backend/.venv frontend/.venv     # optional: remove the Python environments (uv sync recreates them)
```

---

## Versions this project was tested with

Python 3.13 locally and 3.12 in Docker (anything ≥ 3.12 works) · PostgreSQL 16 · uv 0.13 · FastAPI 0.165 · Pydantic 2.14 · SQLAlchemy 2.0.58 · Alembic 1.20 · Logfire 5.6 · Streamlit 1.67.
Exact versions of every package are in `backend/uv.lock` and `frontend/uv.lock`.

**Next:** [BUILD-ORDER.md](BUILD-ORDER.md) (in which order to write the files) and [00-learning-path.md](00-learning-path.md) (the overnight plan).
