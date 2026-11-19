# Enterprise Best Practices

What separates a *demo* from a system a company can **run, trust and change** for years. Each section says what TeamDesk already does, and what you'd add next.

## 1. Structure & design

| Principle | In TeamDesk | Why |
|---|---|---|
| **Layered architecture** (routes → services → models) | ✅ | rules testable and reusable without HTTP |
| **Separate API schema from DB model** | ✅ | change one without breaking the other; no field leaks |
| **Domain exceptions** instead of HTTP errors in business code | ✅ | same rules usable from jobs/CLI |
| **Dependency injection** | ✅ `Depends` | swap parts in tests |
| **Config in environment** (12-factor) | ✅ `pydantic-settings` | same image, any environment |
| **Fail fast on bad config** | ✅ production refuses default secret | catch errors at boot, not at 3 a.m. |
| Single responsibility per module; small functions | ✅ | readability |
| Modular monolith first, microservices only when needed | ✅ | microservices multiply operational cost |

## 2. API design

* **Version** the API (`/api/v1`). **Consistent errors** (`detail`, `code`, `request_id`).
* **Pagination** with a response envelope (`items, total, page, size, pages`). For huge tables switch to **keyset pagination** (`?after_id=...`).
* Use proper verbs/status codes; `PATCH` for partial update; `DELETE` → `204`.
* **Idempotency:** `PUT`/`DELETE` are naturally idempotent; for `POST` that must not duplicate (payments) accept an `Idempotency-Key` header and store results.
* **Never break clients silently:** add fields freely, remove only in a new version, deprecate with notice.
* Document with OpenAPI (free); consider generating typed clients from it.
* Rate-limit by user/IP; return `429` with `Retry-After`.

## 3. Data & migrations

* DB enforces integrity (constraints, FKs, unique); app handles the errors.
* **Every schema change is a reviewed migration**; CI runs `alembic upgrade head` + `alembic check`.
* **Backward-compatible migrations** (expand → migrate → contract) so rollbacks are possible.
* `TIMESTAMPTZ` in UTC; money as `NUMERIC`; surrogate keys; explicit constraint names.
* **Backups with tested restores**, point-in-time recovery, a documented RPO/RTO.
* **Connection pooling** sized to workers (`pool_size`); use **PgBouncer** when many app instances connect.
* **Soft delete** (`deleted_at`) when records must be recoverable or auditable; hard delete for personal-data erasure requests.
* Read replicas for heavy reporting; partition very large tables (e.g. `audit_logs` by month).

## 4. Security (see [06](06-auth-and-security.md))

Hash with Argon2 · short-lived tokens + refresh · RBAC **and** ownership checks server-side · rate limits · MFA/SSO via OIDC · secrets manager · HTTPS · least-privilege DB user · dependency & image scanning · audit trail · privacy: log IDs not people, define data-retention.

## 5. Observability & operations (see [07](07-logfire-observability.md))

* Structured logs, traces, metrics; **request IDs** across services.
* **Health endpoints:** liveness vs readiness (✅).
* **SLOs and alerts** on user-visible symptoms (error rate, p95 latency), not CPU graphs.
* Runbooks for common incidents; blameless post-mortems.
* **Graceful shutdown** (✅ `exec` in entrypoint + lifespan).
* Feature flags for risky changes; canary or blue/green deploys.

## 6. Testing & delivery (see [10](10-testing.md))

| Practice | Status |
|---|---|
| Automated tests on every push (CI) | ✅ `.github/workflows/ci.yml` |
| Lint / format (`ruff`) | ✅ |
| Migrations verified in CI | ✅ |
| Docker images built in CI | ✅ |
| Reproducible installs: `uv.lock` committed, `uv sync --locked` in CI and Docker | ✅ |
| Add: type checking (`mypy`/`pyright`), coverage gates, security scans (`pip-audit`, Trivy) | next step |
| Add: continuous deployment to staging, smoke tests, automatic rollback | next step |

### Branch & release habits
Short-lived branches → pull request → CI green + review → merge → deploy. Tag releases (`v1.2.0`), keep a CHANGELOG, **pin dependencies** (✅) and update them regularly (Dependabot/Renovate).

## 7. Performance & scaling

* **Stateless app servers** → scale horizontally behind a load balancer (`WEB_CONCURRENCY` for processes). Keep state in the DB/cache, not in memory.
* Fix **N+1** queries first, add **indexes** second, **cache** third, scale **hardware** last.
* **Cache** read-heavy, rarely-changing data (Redis); define invalidation up front; cache per-user when data is user-specific.
* **Background jobs** (Celery / RQ / Arq / cloud queues) for email, reports, imports; make jobs idempotent, retried, and observable.
* **Async stack** (`async def` + async driver) ✅ TeamDesk: one process serves many requests; independent queries run in parallel ([14](14-async-and-parallelism.md)). Budget connections: `simultaneous requests × queries per request`.
* **Measure before optimizing** (traces + `EXPLAIN ANALYZE`).

## 8. Team habits that matter more than any tool
1. **Write decisions down** (short ADRs: context, decision, consequences). The *why* is lost fastest.
2. Make the right thing the easy thing: `make up`, `make test`, one-command setup.
3. Small PRs, fast reviews, shared ownership.
4. **Document the "happy path" and the "oh no" path** (SETUP + runbooks).
5. Prefer boring technology you understand over fashionable technology you don't.

## 9. Before going to production, change these

| In this learning project | In production |
|---|---|
| Demo users with a public password (`SEED_DEMO_DATA`) | disabled; real onboarding / SSO |
| Default `SECRET_KEY` allowed locally | random 48+ char secret from a secrets manager (the app already refuses to start otherwise) |
| DB port `5432` published on the host | internal network only; managed DB with backups |
| Migrations run by the API container at start-up | a one-off release job |
| Single container per service | multiple replicas + health-probed rollout |
| HTTP | HTTPS via ingress / load balancer |
| `CORS_ORIGINS` = localhost | your real UI origin(s) |
| Token expiry 60 min, no refresh | short access + refresh tokens (or OIDC) |
| No rate limiting | gateway or `slowapi` |
| Console + optional Logfire | alerts, dashboards, retention policy |

## 10. A scaling roadmap for TeamDesk
1. Cache dashboard stats in Redis (30 s) → shared across API replicas.
2. Move email/notification work to a queue + worker container.
3. Add attachments (object storage, signed URLs, virus scan).
4. Add an SLA/escalation worker (scheduled job).
5. Switch heavy list endpoints to keyset pagination.
6. Add OIDC login; keep roles in your DB.
7. Add `pgvector` for semantic "similar tickets" search (the AI-engineering extension).
8. Split read-heavy reporting onto a replica.

Each of these is a worked challenge in [13-exercises.md](13-exercises.md).
