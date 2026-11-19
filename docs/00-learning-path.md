# Learning Path: one night, start to finish

**Goal:** by morning you can explain, build and debug each layer of a full-stack Python application, and you have run every concept at least once.

**How this repo teaches:** *doc (the idea, 10 min)* → *notebook (try it, 45-75 min)* → *read the real code in `backend/` or `frontend/` (15 min)*.
The notebooks are already executed, so you can read the outputs even before you run anything.

## The plan (about 10 hours with breaks)

| Clock | Block | Read first | Do | Real code to read afterwards |
|---|---|---|---|---|
| 0:00 | **Setup + tour** | [SETUP](SETUP.md), [Architecture](01-architecture.md) | Run the app, click every page | n/a |
| 0:45 | **Pydantic** | [02](02-pydantic.md) | Notebook **01** | `backend/app/schemas/ticket.py` |
| 1:45 | ☕ break | | | |
| 2:00 | **PostgreSQL** | [03](03-postgresql.md) | Notebook **02** | `backend/alembic/versions/*initial*.py` |
| 3:15 | **SQLAlchemy + Alembic** | [04](04-sqlalchemy-alembic.md) | Notebook **03** | `backend/app/models/`, `services/tickets.py` |
| 4:15 | ☕ break | | | |
| 4:30 | **FastAPI** | [05](05-fastapi.md) | Notebook **04** | `backend/app/api/`, `main.py` |
| 5:45 | **Auth & security** | [06](06-auth-and-security.md) | Notebook **05** | `core/security.py`, `api/deps.py` |
| 6:30 | **Logfire** | [07](07-logfire-observability.md) | Notebook **06** | `core/observability.py` |
| 7:15 | ☕ break | | | |
| 7:30 | **Streamlit + testing** | [08](08-streamlit.md), [10](10-testing.md) | Notebook **07** | `frontend/`, `backend/tests/` |
| 8:30 | **Docker + end-to-end** | [09](09-docker-compose.md) | Notebook **08** | `docker-compose.yml`, `Dockerfile` |
| 9:15 | **Async & parallelism** | [14](14-async-and-parallelism.md) | Notebook **09** | `db/session.py`, `core/concurrency.py`, `services/tickets.py` |
| 10:15 | **Prove it** | [11](11-enterprise-best-practices.md), [13](13-exercises.md) | 2-3 challenges | your own code |

Also keep open: [ALEMBIC.md](ALEMBIC.md) (migrations from zero, read it with block 3) and [BUILD-ORDER.md](BUILD-ORDER.md) (in which order to write the files).

### Short on time? (4-hour version)
Setup → notebook **01** (skim), **02** (sections 1-8), **04**, **05**, **08**, **09** (sections 1-6) → one exercise from [13](13-exercises.md).

### How to study well
1. **Predict, then run.** Before each cell, guess the output. Surprises are where learning happens.
2. **Break things on purpose.** Change a type, delete a `Depends`, remove an index, and watch the error.
3. **Say it out loud.** After each notebook, explain its "mental model" in two sentences, as if to a teammate.
4. **Keep a "why" list.** For every design choice in the code ("why 404 instead of 403?"), write the reason. The answers are in the docs.
5. **Type, don't paste**, at least for the exercises.

## The five foundations (what to be *confident* about)

| Foundation | You are confident when you can... |
|---|---|
| **Data modelling** (Pydantic, SQL) | design a table with the right constraints and write the matching Pydantic model |
| **Layering** (routes → services → models) | decide which layer a new rule belongs in |
| **Security** (hashing, JWT, roles, ownership) | name the checks an endpoint needs and where they live |
| **Observability** (logs, spans, request IDs) | find *why* a request was slow or failed from telemetry alone |
| **Delivery** (migrations, Docker, tests, CI) | change the schema, ship it, and roll it back safely |

## Self-check (answer without looking)
1. Why does Pydantic return `422` and not `400`?
2. What is the difference between `flush()` and `commit()`?
3. How would you spot an N+1 problem, and how do you fix it?
4. Why do we answer **404** for someone else's ticket?
5. Why does the backend container run migrations *before* starting the server?
6. What does `exclude_unset=True` solve in a PATCH endpoint?
7. Why is blocking code inside `async def` dangerous, and how does TeamDesk keep Argon2 hashing from causing it?
8. What is the difference between `environment:` and `env_file:` in Compose, and which wins?
9. Why does each parallel query need its own session, and what is the cost?
10. What is the difference between `alembic upgrade head`, `alembic check` and `alembic stamp head`?

*(Answers are in the docs and notebooks: [02](02-pydantic.md), [04](04-sqlalchemy-alembic.md), [ALEMBIC](ALEMBIC.md), [05](05-fastapi.md), [06](06-auth-and-security.md), [09](09-docker-compose.md), [14](14-async-and-parallelism.md).)*
