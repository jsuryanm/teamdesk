# Testing

**In one sentence:** tests are the safety net that lets you change code (or upgrade a library) without fear.
**Hands-on:** notebook `07_streamlit_and_testing` (sections 6-7) · **Real code:** `backend/tests/`, `frontend/tests/`

## Run them
```bash
cd backend  && uv run pytest -q        # 38 tests, needs PostgreSQL + a teamdesk_test database   (make test)
cd frontend && uv run pytest -q        # 6 tests, no services needed                              (make test-ui)
uv run pytest -k printer -x -v         # run matching tests, stop at the first failure, verbose
```

## The shape of a good test: Arrange → Act → Assert
```python
async def test_requester_only_sees_own_tickets(client, auth, make_user, create):
    alice, bob = await make_user(), await make_user()                              # ARRANGE
    mine, theirs = await create(alice, title="Alice"), await create(bob, title="Bob")
    listing = (await client.get("/api/v1/tickets", headers=auth(alice))).json()    # ACT
    assert [t["id"] for t in listing["items"]] == [mine["id"]]                    # ASSERT
    assert (await client.get(f"/api/v1/tickets/{theirs['id']}", headers=auth(alice))).status_code == 404
```

## The testing pyramid (what to write most of)

```
        ▲   few  - end-to-end (UI → API → DB in Docker)       slow, brittle, high confidence
       ╱ ╲
      ╱   ╲  some - API/integration tests (async HTTP client + real PostgreSQL)   ← TeamDesk's sweet spot
     ╱     ╲
    ╱───────╲ many - unit tests (pure functions, Pydantic models)         fast, precise
```

| Level | In TeamDesk | Speed |
|---|---|---|
| Unit | `test_schemas.py` (Pydantic rules, settings) | milliseconds |
| Integration (API + DB) | `test_auth.py`, `test_tickets.py`, `test_health.py` | ~0.1 s each |
| UI | `frontend/tests/test_app.py` with `AppTest` + fake client; `test_client.py` for the parallel API client (`httpx.MockTransport`) | ~1 s |
| End to end | notebook 08 (manual, against the running stack) | seconds |

## How the backend test setup works (`tests/conftest.py`)

1. **Real PostgreSQL.** We rely on JSONB, generated columns and GIN indexes; SQLite would hide real bugs.
2. **Async tests.** `pytest-asyncio` (`asyncio_mode = "auto"`) lets tests be `async def`; the app is called in-process with `httpx.AsyncClient(transport=ASGITransport(app=app))`: no server, no network.
3. **Clean tables after every test.** An autouse fixture `TRUNCATE`s all tables (`RESTART IDENTITY`) after each test, so tests stay independent. We commit for real instead of rolling back one big transaction because the API runs some queries **in parallel on other connections**, and another connection cannot see uncommitted rows.
4. **`NullPool` in tests.** Each test gets its own event loop; no pooled connection may outlive its loop.
5. **Environment set before import.** `conftest.py` sets `DATABASE_URL`/`ENVIRONMENT` *before* importing the app (settings are read at import time).
6. **Factories as fixtures.** `await make_user(role)`, `auth(user)`, `await create(user, ...)` build data and tokens in one line.
7. **Sync engine for housekeeping.** Schema creation and truncation use a simple sync engine (independent of event loops).

```
async test ─► httpx.AsyncClient ─► ASGI app ─► services ─► AsyncSession(s) ─► PostgreSQL (real)
                                                                                   │
                                      TRUNCATE all tables after each test  ◄───────┘
```

## What each file protects

| File | Highlights |
|---|---|
| `test_schemas.py` | trimmed/normalised input, null & empty PATCH rejected, typo'd params rejected, production refuses default secret |
| `test_auth.py` | register/login, no role choice on sign-up, identical errors for unknown user vs wrong password, **deactivated user's existing token stops working**, admin-only routes |
| `test_tickets.py` | visibility (404 not 403), filters + full-text search + priority sorting + pagination, **status state machine**, requester permission matrix, comments rules, audit JSON, stats scoping |
| `test_health.py` | liveness, readiness (DB), OpenAPI contains our routes |
| `test_concurrency.py` | `gather_all` runs concurrently, keeps order, cancels siblings on failure; 30 parallel requests stay consistent; password hashing doesn't block the event loop |

## What to test

| Test | Skip |
|---|---|
| **Every permission rule**, both *allowed* and *denied* | the framework's own behaviour (FastAPI parses JSON fine) |
| Business rules and state transitions | trivial getters |
| Edge cases: empty, huge, duplicate, wrong type | implementation details (private functions) |
| **Bug found in production → failing test first**, then fix | tests that mirror the code line by line |

## pytest toolbox
| Tool | Use |
|---|---|
| `@pytest.fixture` | reusable setup, injected by argument name |
| `@pytest.mark.parametrize` | one test, many inputs |
| `pytest.raises(...)` | expect an exception |
| `monkeypatch` | temporarily change env vars / attributes (auto-undone) |
| `-k expr`, `-x`, `--lf`, `-s`, `--pdb` | select, stop early, re-run failures, show prints, debugger |
| `pytest-asyncio` | `async def` tests and fixtures (`asyncio_mode = "auto"`) |
| `pytest-cov` | coverage report (`uv add --dev pytest-cov`, then `pytest --cov=app`) |

## Best practices
1. One behaviour per test; name it like a sentence.
2. Tests must be **independent** and runnable in any order.
3. Don't mock what you own: use the real DB; mock **external** services (payment, email) at the boundary.
4. Keep tests fast so people actually run them (and CI runs them on every push).
5. Test through the **public interface** (HTTP), so refactors don't break tests.
6. Treat a flaky test as a bug; fix or delete it.
7. Add a regression test with every bug fix.

## CI
`.github/workflows/ci.yml` runs on every push/PR: **`uv sync --locked` → lint (ruff) → apply migrations → `alembic check` → backend tests → frontend tests → build Docker images**. It starts a PostgreSQL service container just like `docker compose` would.

## Practice
* Write the failing test for "an agent cannot delete a ticket" first, then confirm it already passes. What does that tell you?
* Add a parametrized test over all invalid status transitions.
* Run `pytest --cov=app --cov-report=term-missing` and add tests until `services/` is above 95 %.
