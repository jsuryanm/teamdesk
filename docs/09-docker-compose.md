# Docker & Docker Compose

**In one sentence:** Docker packages your app *and everything it needs* into an image that runs identically anywhere; Compose starts several such containers together.
**Hands-on:** notebook `08_docker_compose_and_end_to_end` · **Real code:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/docker-entrypoint.sh`

## Mental model: shipping containers for software

| Term | Analogy | In TeamDesk |
|---|---|---|
| **Image** | sealed, frozen package built from a recipe | `teamdesk-backend` |
| **Dockerfile** | the recipe | `backend/Dockerfile` |
| **Container** | a running copy of an image (disposable) | the running API |
| **Volume** | a USB drive that outlives the container | `pgdata` (your database files) |
| **Network** | private LAN; containers reach each other **by service name** | `backend` calls `db:5432` |
| **Compose** | conductor of the orchestra | `docker-compose.yml` |

## Commands you'll use every day

```bash
docker compose up --build -d        # build + start in background      (make up)
docker compose ps                   # status + health
docker compose logs -f backend      # follow one service's logs
docker compose exec db psql -U teamdesk -d teamdesk     # shell inside a container  (make psql)
docker compose exec backend alembic current
docker compose restart backend
docker compose down                 # stop, KEEP data
docker compose down -v              # stop and DELETE data (fresh start)     (make reset)
docker compose --profile learn up   # also JupyterLab on :8888 (token: teamdesk)
docker compose --profile tools up   # also Adminer (DB web UI) on :8080
```

## Reading `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]       # data survives container deletion
    healthcheck: {test: ["CMD-SHELL", "pg_isready ..."], interval: 5s, retries: 10}
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg://...@db:5432/...   # host is "db", not "localhost"!
    depends_on:
      db: {condition: service_healthy}                      # wait for HEALTHY, not just started
  frontend:
    environment: {API_URL: http://backend:8000}
    depends_on: {backend: {condition: service_healthy}}
```

### Why `db` and not `localhost`?
Every container has **its own** `localhost`. Compose creates a network where each service's **name is its hostname**.
So the backend reaches the database at `db`, the UI reaches the API at `backend`.

### Start-up order
`db` (healthy) → `backend` (migrations → seed → server → healthy) → `frontend`.
`depends_on` *without* `condition: service_healthy` only waits for the container to **start**, not for Postgres to be ready (a classic source of "connection refused" at boot).

### Where settings come from (highest priority first)
1. `environment:` in the compose file
2. `env_file:` (`.env`)
3. defaults: `${POSTGRES_USER:-teamdesk}` in compose, or defaults in code

That's why it works with **zero** config, and why `DATABASE_URL` in `.env` (pointing at `localhost`, for running Python on your laptop) doesn't break the container (compose overrides it with the `db` address).

### Profiles
`jupyter` (`learn`) and `adminer` (`tools`) are **opt-in**: they don't start unless you ask. Great for dev tools you don't want in normal runs.

## The Dockerfile, line by line (backend)

| Line / idea | Why |
|---|---|
| `FROM python:3.12-slim AS builder` … `COPY --from=builder` | **multi-stage**: install in one stage, copy only the result → smaller, safer image |
| `COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv ...` | **uv** comes from its official image, version-pinned |
| `COPY pyproject.toml uv.lock ./` then `RUN uv sync --locked --no-dev` **before** `COPY . .` | **layer caching**: code edits don't reinstall dependencies. `--locked` fails if the lock is stale; `--no-dev` leaves test tools out |
| `UV_PROJECT_ENVIRONMENT=/opt/venv` | the virtualenv lives at a fixed path we copy into the runtime image |
| `useradd ... USER appuser` | **never run as root** in a container |
| `HEALTHCHECK ... /health/live` | Docker/Compose/Kubernetes know when it's alive |
| `ENTRYPOINT ["sh", "./docker-entrypoint.sh"]` | run migrations → seed (optional) → start the server |
| `exec uvicorn ...` in the script | server becomes **PID 1**: receives `SIGTERM`, shuts down gracefully |
| `PYTHONUNBUFFERED=1` | logs appear immediately |
| pinned versions (`postgres:16-alpine`, `uv.lock`, the uv image tag) | reproducible builds |
| `.dockerignore` | keep `.env`, tests, caches out of the image |

## Best practices
1. **One process per container.** Compose combines containers; don't cram them together.
2. **Config via environment variables**, never baked into images; secrets never in the Dockerfile or git.
3. Pin base-image versions (`python:3.12-slim`, not `latest`).
4. Add `HEALTHCHECK`s and use `service_healthy` ordering.
5. Run as **non-root**; keep images small (slim, multi-stage).
6. Persist state **only** in volumes; containers must be disposable.
7. Order Dockerfile steps from *least to most frequently changed* (cache!).
8. Don't publish ports you don't need (`5432:5432` is for learning; remove it in production).

## Common mistakes
| Mistake | Fix |
|---|---|
| Using `localhost` between containers | use the service name |
| `depends_on` without health | add a healthcheck + `condition: service_healthy` |
| Editing code but seeing old behaviour | rebuild: `docker compose up --build` |
| Losing data on `down -v` | volumes are deleted by `-v`; plain `down` keeps them |
| `latest` tags | pin versions |
| Secrets in `docker-compose.yml` committed to git | `.env` (ignored), a secrets manager in production |
| Running migrations from *every* replica at once | run migrations as a **one-off job**; the entrypoint approach is for single instances |

## From Compose to production
Compose is perfect for **development, demos, CI and single-host deployments**. For production at scale you'd typically:
* push images to a **registry**, deploy with **Kubernetes / ECS / Cloud Run / Nomad**
* use a **managed PostgreSQL** (RDS, Cloud SQL, Azure DB) with automated backups
* run migrations as a **release job** before rolling out
* use the same `/health/live` and `/health/ready` endpoints as **liveness / readiness probes**
* inject secrets from a **secret manager**, terminate TLS at an **ingress / load balancer**

## Practice
* Run `docker compose up -d db`, then `docker compose exec db psql ...` and list tables.
* Stop only the backend (`docker compose stop backend`); what does the UI show? Start it again.
* Add a `redis` service and a `REDIS_URL` setting (see exercise "Cache the stats").
* Shrink the image: compare `docker images` sizes before/after removing the multi-stage build.
