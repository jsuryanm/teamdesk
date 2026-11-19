# FastAPI: your functions, as a web API

**In one sentence:** FastAPI turns Python functions with type hints into a validated, documented HTTP API.
**Hands-on:** notebook `04_fastapi_basics_to_advanced` · **Real code:** `backend/app/main.py`, `backend/app/api/`

## Mental model
A **waiter**: takes the order (path, query, body), checks it against your type hints (Pydantic), fetches what your function asked for (**dependencies**), calls your function, and serves the result. It also prints the menu automatically: **`/docs`**.

## The essentials

```python
@router.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: DbSession, user: CurrentUser):    # every parameter is "asked for"
    return tickets.get_ticket(db, ticket_id, user)
```
| Where the value comes from | How FastAPI knows |
|---|---|
| URL path `/tickets/5` | name appears in the path → `ticket_id: int` |
| Query string `?page=2` | simple type not in path → `page: int = 1` |
| JSON body | a Pydantic model → `data: TicketCreate` |
| Headers / cookies | `Header()`, `Cookie()` |
| A dependency | `Depends(...)` or an `Annotated[...]` alias |

### Status codes
`200` OK · `201` created · `204` no content · `400` bad request · `401` not authenticated · `403` not allowed · `404` not found · `409` conflict (rule violated) · `422` validation failed · `500` our bug.
**401 vs 403:** 401 = "who are you?", 403 = "I know you, but no".

## Dependency injection (the superpower)
A dependency is a function your endpoint *asks for*. FastAPI calls it and passes the result in; dependencies can have dependencies.

```python
DbSession   = Annotated[Session, Depends(get_db)]          # yields a session, closes it afterwards
CurrentUser = Annotated[User,    Depends(get_current_user)]# needs the token AND the db session
StaffUser   = Annotated[User,    Depends(require_roles(Role.ADMIN, Role.AGENT))]
```
Why it's great: **reuse** (one line adds auth to an endpoint), **cleanup** (`yield` always runs `finally`), **testability** (`app.dependency_overrides[get_db] = lambda: test_session`).

Resolved tree for `GET /tickets`: `get_db`, `get_current_user → (oauth2 scheme, get_db, get_settings)`. Notebook 04 prints it.

## Project structure used here

```
app/main.py         create_app(): middleware, exception handlers, routers, observability
app/api/router.py   /api/v1 prefix; includes routers
app/api/routes/     auth.py users.py tickets.py health.py   (thin!)
app/api/deps.py     DbSession, CurrentUser, StaffUser, AdminUser
app/services/       business rules (no FastAPI imports)
```
A good route is **3-5 lines**: validate (automatic) → call service → return.

## Errors, the professional way
Services raise **domain exceptions** (`NotFoundError`, `ConflictError`, `PermissionDeniedError`). One handler in `main.py` converts them:

```json
{"detail": "Ticket not found", "code": "not_found", "request_id": "3f2a..."}
```
Same shape everywhere → clients and support can rely on it. The `request_id` ties an error report to logs and traces.

## Middleware
Code around *every* request. TeamDesk's adds `X-Request-ID` (reused from the caller or generated) and puts it into Logfire baggage so every log line of that request carries it. CORS is also middleware (only the Streamlit origin is allowed).

## Lifespan
```python
@asynccontextmanager
async def lifespan(app):
    logfire.info("starting")      # startup: open pools, warm caches
    yield
    await engine.dispose()        # shutdown: release resources
```
Replaces the old `@app.on_event`.

## `def` or `async def`?
| | runs on | safe to call blocking code (psycopg, requests, `time.sleep`)? |
|---|---|---|
| `def` | **thread pool** | ✅ yes |
| `async def` | **event loop** | ❌ no: it freezes *every* request |

Notebook 04 measures it (5 requests × 0.3 s): `def` 0.30 s · `async` + `await` 0.30 s · `async` + blocking **1.51 s**.
TeamDesk is **async end to end**: `async def` routes, async SQLAlchemy, and the one slow blocking step (Argon2 hashing) moved to `asyncio.to_thread`. That is the rule: *an `async def` route is only as good as the blocking calls inside it.* A `def` route with a sync DB is also correct (FastAPI runs it in a thread pool), but mixing `async def` with sync DB calls is the classic performance bug. See [14-async-and-parallelism.md](14-async-and-parallelism.md).

## Details worth knowing
* **Route order matters:** declare `/tickets/stats` **before** `/tickets/{ticket_id}`, or "stats" is parsed as an id (→ 422).
* **Query parameter models:** `filters: Annotated[TicketFilters, Query()]` validates a whole query string as one model.
* **Response models filter output:** return an ORM object, clients get only the declared fields.
* **Versioning:** everything lives under `/api/v1` so `/api/v2` can coexist.
* **Health endpoints:** `/health/live` (is the process up?) and `/health/ready` (can it reach the DB?). Orchestrators use them; they're excluded from tracing.
* **OpenAPI:** `/docs` (Swagger UI), `/redoc`, `/openapi.json`. Generate typed clients from it.
* **`BackgroundTasks`:** fine for light, loss-tolerant work after the response (e.g. send an email). For important jobs use a real queue.

## Best practices
1. Keep routes thin; **rules live in services**.
2. Always declare `response_model` (or return type): it's a security filter.
3. Use `Annotated` dependency aliases; they read like English.
4. Return **proper status codes**; don't return `200` with `{"error": ...}`.
5. Never import `HTTPException` in services.
6. Don't do blocking work in `async def`.
7. Version your API; keep error shape consistent; document with docstrings (they appear in `/docs`).
8. Validate at the edge, authorize in the service, constrain in the database: **three independent lines of defence**.

## Common mistakes
| Mistake | Effect |
|---|---|
| Business logic inside route functions | untestable, duplicated |
| Forgetting `response_model` | leaks fields like `hashed_password` |
| Opening a DB session manually per function | leaks connections; use `Depends(get_db)` |
| `async def` + sync DB calls (or any blocking call) | slow under load: freezes every request |
| Catching all exceptions and returning 200 | hides bugs from monitoring |
| Global mutable state | breaks with multiple workers |

## Run it
```bash
cd backend && uvicorn app.main:app --reload          # dev
WEB_CONCURRENCY=4 uvicorn app.main:app               # 4 worker processes
```
Open http://localhost:8000/docs → **Authorize** (email in `username`, password) → try endpoints.

## Practice
* Add `GET /api/v1/tickets/{id}/watchers` end to end (model → migration → service → route → test).
* Add a middleware that logs a warning when a request takes more than 500 ms.
* Make `GET /tickets` return an `ETag` and honour `If-None-Match`.
