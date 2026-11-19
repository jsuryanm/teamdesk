# Cheat Sheet & Glossary

## Commands

```bash
# Run everything
docker compose up --build -d      docker compose logs -f      docker compose down  (-v to wipe data)
# Local dev (uv: no virtualenv activation needed)
docker compose up -d db
cd backend && uv sync                      cd frontend && uv sync
cd backend && uv run alembic upgrade head && uv run python -m app.seed
cd backend && uv run uvicorn app.main:app --reload
cd frontend && uv run streamlit run app.py
# Tests / lint
cd backend && uv run pytest -q             cd frontend && uv run pytest -q
cd backend && uv run ruff check .
# uv
uv add httpx   uv add --dev pytest-cov   uv remove httpx   uv lock --upgrade   uv sync --locked   uv run <cmd>
# Migrations (details: ALEMBIC.md)
uv run alembic revision --autogenerate -m "msg"   uv run alembic upgrade head    uv run alembic downgrade -1
uv run alembic current   uv run alembic history   uv run alembic check
# Database shell
docker compose exec db psql -U teamdesk -d teamdesk       \dt  \d tickets  \di  \x  \q
```

## URLs
| | |
|---|---|
| UI | http://localhost:8501 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health | `/health/live`, `/health/ready` |
| JupyterLab (`--profile learn`) | http://localhost:8888 (token `teamdesk`) |
| Adminer (`--profile tools`) | http://localhost:8080 (server `db`, user/password/db = `teamdesk`) |

## Demo accounts (password `Password123!`)
`admin@teamdesk.dev` · `agent@teamdesk.dev` · `agent2@teamdesk.dev` · `user@teamdesk.dev` · `user2@teamdesk.dev`

## API quick tour (curl)
```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/token -d "username=admin@teamdesk.dev&password=Password123!" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" "localhost:8000/api/v1/tickets?q=printer&status=open&sort=priority&size=5"
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/tickets/stats
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"title":"Test ticket","description":"hello","priority":"high","tags":["demo"]}' localhost:8000/api/v1/tickets
```

| Method & path | Who | Purpose |
|---|---|---|
| `POST /api/v1/auth/register` | anyone | create a requester account |
| `POST /api/v1/auth/token` | anyone | log in (form: `username`=email, `password`) |
| `GET /api/v1/users/me` | logged in | who am I |
| `GET/POST /api/v1/users`, `PATCH /users/{id}` | staff / admin | list, create, change role/active |
| `POST /api/v1/tickets` | logged in | create ticket |
| `GET /api/v1/tickets` | logged in | list (filters: `status`, `priority`, `q`, `tag`, `unassigned`, `assignee_id`, `sort`, `order`, `page`, `size`) |
| `GET /api/v1/tickets/stats` | logged in | dashboard numbers (scoped to your visibility) |
| `GET/PATCH /api/v1/tickets/{id}` | owner or staff | read / update |
| `POST /api/v1/tickets/{id}/assign` | staff | assign / unassign |
| `GET/POST /api/v1/tickets/{id}/comments` | owner or staff | comments |
| `GET /api/v1/tickets/{id}/history` | staff | audit trail |
| `DELETE /api/v1/tickets/{id}` | admin | delete |

## Status workflow
```
open ──► in_progress ──► resolved ──► closed
  ▲          │               │           │
  └──────────┴───────────────┴───────────┘   (reopen: any → open; closed can only reopen)
```
Allowed: `open → in_progress | resolved | closed`; `in_progress → open | resolved | closed`; `resolved → open | closed`; `closed → open`.

## Python snippets you'll reuse

```python
# Pydantic
class M(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    x: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
M.model_validate(data);  m.model_dump(exclude_unset=True)

# FastAPI
DbSession = Annotated[Session, Depends(get_db)]
@router.get("/{id}", response_model=Out)
def read(id: int, db: DbSession, user: CurrentUser): ...

# SQLAlchemy (async: await every DB call; no lazy loading)
(await db.scalars(select(T).where(T.x == 1).options(selectinload(T.items)))).all()
await db.get(T, 1);  db.add(obj);  await db.flush();  await db.commit();  await db.rollback()

# Parallel work (core/concurrency.py): independent queries, each on its OWN session
a, b = await gather_all(query_one(db), in_new_session(query_two))
await asyncio.to_thread(hash_password, pw)   # blocking/CPU work off the event loop

# Logfire
logfire.info("did {thing}", thing=x);  with logfire.span("work {id}", id=1): ...

# Streamlit
st.session_state.setdefault("page", 1);  st.rerun();  @st.cache_data(ttl=30)
```

## HTTP status codes
`200` OK · `201` Created · `204` No Content · `400` Bad Request · `401` Not authenticated · `403` Forbidden · `404` Not Found · `409` Conflict · `422` Validation error · `429` Too Many Requests · `500` Server error · `503` Unavailable

## Glossary

| Term | Plain meaning |
|---|---|
| **ACID** | Atomic, Consistent, Isolated, Durable: the guarantees of a database transaction |
| **Alembic** | tool that applies versioned schema changes (migrations); see [ALEMBIC.md](ALEMBIC.md) |
| **API** | a set of URLs other programs call to use your system |
| **Argon2** | a deliberately slow password-hashing algorithm |
| **Async** | code that can wait for I/O without blocking others (`async`/`await`) |
| **Event loop** | the single scheduler that runs all async code in a process; one blocking call freezes everything |
| **TaskGroup** | runs tasks concurrently; if one fails the others are cancelled |
| **uv** | fast Python package/environment manager; `uv.lock` pins every version |
| **Lock file** | exact versions of all packages, so every machine installs the same thing |
| **Authentication** | proving who you are |
| **Authorization** | deciding what you may do |
| **Bearer token** | a token sent as `Authorization: Bearer <token>` |
| **CI/CD** | automatically testing (CI) and deploying (CD) every change |
| **Constraint** | a rule the database enforces (NOT NULL, UNIQUE, CHECK, FK) |
| **Container** | a running, isolated instance of an image |
| **CORS** | browser rule about which websites may call your API |
| **CRUD** | Create, Read, Update, Delete |
| **CTE** | `WITH` clause: a named sub-query |
| **Dependency (FastAPI)** | a function whose result is injected into your endpoint |
| **Dependency injection** | passing in what a function needs instead of creating it inside |
| **Domain exception** | an error that describes a business problem, not an HTTP one |
| **DTO / schema** | a model describing the shape of data crossing a boundary |
| **Eager loading** | fetching related rows up-front to avoid N+1 queries |
| **ENV var** | configuration supplied by the environment |
| **Foreign key** | column pointing to another table's primary key |
| **GIN index** | index type for JSONB / full-text / arrays |
| **Health check** | endpoint/command that says whether a service is alive/ready |
| **Idempotent** | doing it twice has the same effect as doing it once |
| **IDOR** | accessing someone else's data by guessing an ID |
| **Image** | frozen package your container starts from |
| **Index** | structure that makes lookups fast |
| **JSONB** | PostgreSQL's binary, indexable JSON type |
| **JWT** | signed token carrying claims (`sub`, `exp`, ...) |
| **Lifespan** | startup/shutdown hooks of a FastAPI app |
| **Middleware** | code that wraps every request/response |
| **Migration** | a script that moves the database schema one step |
| **N+1 problem** | 1 query for a list plus 1 more per item |
| **ORM** | maps database rows to Python objects (SQLAlchemy) |
| **OpenTelemetry** | open standard for logs, traces, metrics |
| **Pagination** | returning big lists in pages |
| **PID 1** | the first process in a container; receives stop signals |
| **Profile (Compose)** | optional services started only when requested |
| **RBAC** | role-based access control |
| **Readiness / liveness** | "can it serve traffic?" / "is the process alive?" |
| **Request ID** | unique id of one request, carried through all logs |
| **Savepoint** | a bookmark inside a transaction you can roll back to |
| **Service layer** | module holding business rules, between routes and database |
| **Session (SQLAlchemy)** | unit of work tracking changes until commit |
| **Session state (Streamlit)** | per-tab memory surviving script reruns |
| **Span / trace** | a timed operation / the tree of spans for one request |
| **Stateless** | server keeps no per-user memory between requests |
| **tsvector / tsquery** | PostgreSQL full-text search types |
| **Volume** | persistent storage attached to containers |
| **Window function** | calculation across related rows without collapsing them |
| **12-factor app** | principles for portable, cloud-ready apps (config in env, stateless, logs to stdout...) |
