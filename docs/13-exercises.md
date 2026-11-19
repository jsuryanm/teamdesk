# Exercises: turn understanding into confidence

Do **at least one from each level**. Work on a Git branch (`git checkout -b exercise-1`), write the **test first** where possible, and keep `make test` green.
Each exercise lists the layers you'll touch, so you practise the whole stack, not one corner.

> **Method for every exercise:** (1) write down the rule in one sentence → (2) decide which layer owns it → (3) write a failing test → (4) implement → (5) migrate if the schema changed → (6) check the Logfire/console output → (7) update the UI.

---

## 🟢 Level 1: Warm-up (30-45 min each)

### 1. Add a `due_date` to tickets
*Layers: model → **migration** → schema → service → UI*
* Nullable `due_date: date` column. `TicketCreate` accepts it but **rejects past dates** (`field_validator`).
* `GET /tickets?overdue=true` returns tickets past due that are not resolved/closed.
* Show an "Overdue" metric on the dashboard.
* ✔ Done when: `alembic check` passes, `alembic downgrade -1` works, tests cover past-date rejection and the overdue filter.

### 2. "My tickets" for agents
*Layers: filters → service → UI*
* Add `mine: bool` to `TicketFilters` (assigned to me). Add a toggle in the Tickets page.
* ✔ Test: agent A with `mine=true` never sees agent B's tickets.

### 3. Soft-delete tickets
*Layers: model → migration → service → tests*
* Add `deleted_at`. `DELETE` sets it instead of removing the row; all queries exclude deleted tickets. Admin can `POST /tickets/{id}/restore`.
* ✔ Test: a deleted ticket returns 404 for everyone and is absent from stats.

### 4. Better errors in the UI
* When the API returns `409`, show a *warning* (not red error) with a human message. Add an `AppTest` for it.

---

## 🟡 Level 2: Real features (1-2 h each)

### 5. Ticket watchers (many-to-many)
*Layers: new table + migration → service → route → UI → tests*
* Users can watch a ticket. `POST/DELETE /tickets/{id}/watchers/me`, `GET /tickets/{id}/watchers`.
* Rule: a requester can watch only their own tickets; staff can watch any. Write the permission matrix as parametrized tests.

### 6. Refresh tokens
*Layers: security → DB → routes → UI*
* Short access token (5 min) + refresh token (7 days) stored **hashed** in a `refresh_tokens` table; `POST /auth/refresh` rotates it; logout revokes it.
* Streamlit: transparently refresh on `401` once, then log out.
* ✔ Tests: reuse of an old refresh token fails; deactivated user can't refresh.

### 7. Rate-limit login
* Max 5 failed logins per email per 15 minutes → `429` with `Retry-After`. Start with a table (`login_attempts`), then discuss Redis as a better home.
* ✔ Test: the 6th attempt is blocked even with the correct password; success resets.

### 8. SLA timers
* Priority → SLA hours (urgent 4, high 8, medium 24, low 72). Compute `sla_breached` in SQL (`created_at + interval`), expose it in `TicketSummary`, add a dashboard metric, and a Streamlit badge.
* Stretch: show the breakdown as a `GROUP BY priority` with `FILTER`.

---

## 🔴 Level 3: Enterprise-grade (2-4 h each)

### 9. Cache the dashboard in Redis
* Add a `redis` service to Compose, a `REDIS_URL` setting, cache `get_stats` for 30 s **per visibility scope** (requester id or "staff").
* Invalidate on ticket create/update. Add a Logfire span `cache hit/miss`.
* ✔ Prove with traces that the second call issues zero SQL.

### 10. Bound and measure the parallelism
* TeamDesk is already async ([14](14-async-and-parallelism.md)). Add a 5th parallel query to `get_stats` ("resolved today"), then count the connections one request uses.
* Wrap the fan-out in an `asyncio.Semaphore(2)`; compare the traces. Add a load test (50 concurrent `GET /tickets/stats`) and find the pool size where requests start to queue.
* Add `asyncio.timeout(0.5)` around one query and return a friendly `503`. Write the test with a `pg_sleep` query.

### 11. Background worker + email notifications
* Add a `worker` service (Arq or RQ + Redis). On ticket assignment enqueue "notify assignee"; the job writes to an `outbox` table (pretend email).
* Make the job **idempotent** and retried; trace it end-to-end with a propagated trace id.

### 12. Semantic "similar tickets" with pgvector
* Use the `pgvector/pgvector:pg16` image, add an `embedding vector(384)` column + migration + HNSW index.
* Embed titles with any small embedding model; `GET /tickets/{id}/similar` returns the 5 nearest tickets (cosine distance), respecting visibility rules.
* ✔ Test with fake embeddings; discuss why visibility filtering must happen **in the query**, not after.

---

## 🧪 Debugging drills (break it, then fix it)

| Drill | What you learn |
|---|---|
| Remove `joinedload(Ticket.requester)` from `list_tickets` and watch the traces | N+1 recognition |
| Change `depends_on: db` to a plain start-order dependency | why health-based ordering matters |
| Delete the `ix_tickets_status_priority` index and `EXPLAIN` the stats query | index impact |
| Set `ENVIRONMENT=production` without a `SECRET_KEY` | fail-fast configuration |
| Return the ORM `User` from a route **without** `response_model` | what leaks |
| Call `time.sleep(1)` inside an `async def` route and hit it concurrently | blocking the event loop |
| Remove `joinedload(...)` from `list_tickets` | `MissingGreenlet`: no lazy loading in async |
| Set `DB_POOL_SIZE=1 DB_MAX_OVERFLOW=0` and call `/tickets/stats` twice at once | connection-pool queueing |
| Drop the `UNIQUE` constraint on `users.email`, then register twice quickly | why constraints beat checks in code |

---

## ✅ Final self-assessment

You're **confident** if you can, without notes:

- [ ] Sketch the architecture and trace a request from click to database and back.
- [ ] Explain *why* each layer exists and what breaks if you merge two of them.
- [ ] Add a column end-to-end: migration, model, schema, service, test, UI.
- [ ] Find a slow endpoint using only traces, and name the likely fix.
- [ ] List what an endpoint needs to be secure: authentication, role, ownership, validation, audit.
- [ ] Explain every line of the Dockerfile and compose file.
- [ ] Write a test for a bug **before** fixing it.
- [ ] State three things you'd change before running this in production, and why.

If any box is empty, re-open that notebook, and do the matching exercise. Confidence comes from repetition, not from reading.
