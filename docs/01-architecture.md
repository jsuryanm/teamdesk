# Architecture: how the pieces fit

## The big picture

```
┌────────────┐   HTTP + JSON    ┌──────────────────────────── backend (FastAPI) ───────────────────────────┐
│  Streamlit │ ───────────────► │  routes ─► dependencies ─► services ─► SQLAlchemy ─► PostgreSQL           │
│     UI     │ ◄─────────────── │  (HTTP)    (auth, DB)     (rules)      (ORM)         (data)               │
└────────────┘   JWT in header  └───────────────────────────────────────────────────────────────────────────┘
      │                                         │
      └───── traceparent header ────────────────┴──────► Logfire (logs + traces + SQL spans)
```

Three **independent services** (+ database), talking only through an HTTP contract.
The UI never touches the database, and has its own copy of the response models. You could replace Streamlit with React tomorrow and change nothing in the backend.

## Layers inside the backend

| Layer | Folder | Job | Knows about |
|---|---|---|---|
| **Routes** | `app/api/routes/` | Parse the request, call a service, shape the response | HTTP, Pydantic |
| **Dependencies** | `app/api/deps.py` | Provide a DB session, the current user, role checks | FastAPI |
| **Services** | `app/services/` | **Business rules**: permissions, state machine, auditing | SQLAlchemy, domain exceptions |
| **Schemas** | `app/schemas/` | The *shape* of data entering/leaving the API | Pydantic only |
| **Models** | `app/models/` | The *shape* of data in the database | SQLAlchemy only |
| **Core** | `app/core/` | Settings, security helpers, logging setup, exceptions | no web, no DB |

**The golden rule:** dependencies point **downwards**. Routes know services; services know models; models know nothing above them.
Services raise *domain* exceptions (`NotFoundError`), never `HTTPException`, so the same rules could be reused from a CLI or a background worker.

> **Why separate `schemas/` from `models/`?** They change for different reasons. A database column may be added without changing the API,
> and some API fields (like `password`) must never map to the database as-is. Mixing them leaks internals and creates security holes.

## Life of a request: "Create ticket"

1. **Streamlit** form → `TeamDeskClient.create_ticket(...)` → `POST /api/v1/tickets` with header `Authorization: Bearer <JWT>` (httpx adds a `traceparent` header).
2. **Middleware** assigns/reuses `X-Request-ID` and attaches it to every span.
3. **FastAPI** matches the route and resolves dependencies: `get_db` (opens a session) → `get_current_user` (decodes the JWT, loads the user, rejects inactive ones).
4. **Pydantic** validates the body into `TicketCreate` (trims the title, cleans tags). Invalid → `422` with exact field errors.
5. **Service** `create_ticket()` builds the `Ticket`, reuses/creates tags, `flush()` to get the ID, writes an **audit row in the same transaction**, `commit()`.
6. **SQLAlchemy** emits `INSERT`s; **PostgreSQL** applies constraints and computes the generated `search_vector`.
7. **Response model** `TicketRead` filters the ORM object into JSON → `201 Created`.
8. **Logfire** has recorded the request span, each SQL statement span, and our `ticket created` log, all in one trace.
9. **Streamlit** parses the JSON into a `Ticket` Pydantic object and shows it.

## Data model

```
users ──< tickets >── tags          (tickets.requester_id, tickets.assignee_id -> users)
            │  └──< ticket_tags >──┘   (many-to-many)
            └──< comments >── users
audit_logs (actor_id -> users, entity + entity_id, details JSONB)
```

| Table | Notes |
|---|---|
| `users` | unique email, Argon2 hash, `role` (admin / agent / requester), `is_active` |
| `tickets` | status & priority stored as `VARCHAR + CHECK`, composite index `(status, priority)`, generated `search_vector` + GIN index |
| `comments` | cascade-deleted with their ticket |
| `tags` + `ticket_tags` | many-to-many, normalised lower-case names |
| `audit_logs` | append-only, `details` is JSONB (e.g. `{"priority": {"from": "low", "to": "urgent"}}`) |

## Business rules (all in `services/tickets.py`)

| Rule | Where | Why in the service layer |
|---|---|---|
| Requesters see only their own tickets (others → **404**) | `_scope()` | one place, impossible to forget in a route |
| Status follows a state machine (`ALLOWED_TRANSITIONS`) | `update_ticket` | easy to read and unit-test |
| Requesters may only edit open tickets / close their own | `update_ticket` | permission *and* state rules combined |
| Assignee must be an active agent/admin | `assign_ticket` | protects data quality |
| Every change writes an audit row in the same transaction | `audit.record` | log can never disagree with data |
| Closed tickets reject new comments | `add_comment` | domain rule |

## Key design decisions (and the trade-off)

| Decision | Chosen | Alternative | Trade-off |
|---|---|---|---|
| DB access | **async** SQLAlchemy, `async def` routes, independent queries run in parallel | sync SQLAlchemy | One process serves many requests and one request overlaps its waits; costs: no lazy loading, more connections per request ([14](14-async-and-parallelism.md)). |
| Enums | `VARCHAR + CHECK` | native PG `ENUM` | Easier migrations (adding a value is trivial) |
| Pagination | offset/limit (`page`, `size`) | keyset (cursor) | Easy and enough for thousands of rows; keyset scales better to millions |
| Auth | self-issued JWT, 60 min | OIDC/SSO provider | Teaches the mechanics; enterprises usually delegate to an IdP |
| Search | Postgres full-text + GIN | Elasticsearch | No extra infrastructure; good to ~millions of rows |
| Audit | rows in the same DB | event stream | Strong consistency; simple |
| UI | Streamlit | React | All-Python, fastest to build; less control over UX |
| Migrations at start-up | container entrypoint runs `alembic upgrade head` | separate migration job | Simple; with many replicas, run migrations as a one-off job instead |

## What is intentionally *not* here (and where to learn it)
Refresh tokens, rate limiting, caching layer (Redis), background workers, file attachments, email, multi-tenancy.
Each is a graded challenge in [`13-exercises.md`](13-exercises.md); the approach for each is outlined in [`11-enterprise-best-practices.md`](11-enterprise-best-practices.md).
