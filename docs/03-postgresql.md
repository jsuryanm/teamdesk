# PostgreSQL: the database that checks your work

**In one sentence:** PostgreSQL stores your data in tables with **rules the database itself enforces**, so bugs in application code cannot corrupt it.
**Hands-on:** notebook `02_postgres_sql_fundamentals` · **Real code:** `backend/alembic/versions/*initial*.py`

## Mental model
A set of **spreadsheets with strict rules**. Each sheet is a *table*, each line a *row*, each column has a *type*, and *constraints* are rules like "this cell can't be empty" or "this must match a row in another sheet".

## Types worth knowing

| Need | Use | Avoid |
|---|---|---|
| Surrogate key | `BIGINT GENERATED ALWAYS AS IDENTITY` | hand-rolled counters |
| Text | `TEXT` (or `VARCHAR(n)` to enforce a max) | `CHAR(n)` |
| Money / exact numbers | `NUMERIC(10,2)` | `FLOAT` (rounding errors!) |
| Moments in time | `TIMESTAMPTZ` | `TIMESTAMP` without zone |
| Flexible documents | `JSONB` | `JSON` (not indexable) |
| Yes / no | `BOOLEAN` | `0/1` integers |
| Unique ids across systems | `UUID` | |

## Constraints = your safety net

```sql
CREATE TABLE orders (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,   -- FOREIGN KEY
  status      TEXT   NOT NULL DEFAULT 'new' CHECK (status IN ('new','paid')), -- CHECK
  email       TEXT   UNIQUE                                                   -- UNIQUE
);
```
| Constraint | Meaning |
|---|---|
| `PRIMARY KEY` | unique + not null; the row's identity |
| `NOT NULL` | value required |
| `UNIQUE` | no duplicates (race-proof, unlike "check then insert" in code) |
| `CHECK` | any boolean rule |
| `FOREIGN KEY` | must point at an existing row; `ON DELETE` decides what happens when the parent goes: `RESTRICT` (forbid) · `CASCADE` (delete children) · `SET NULL` |

## Queries you must be fluent in

```sql
-- filter / sort / page
SELECT id, title FROM tickets WHERE status = 'open' ORDER BY created_at DESC LIMIT 20 OFFSET 40;

-- join: rows that match on both sides (LEFT JOIN keeps unmatched left rows)
SELECT t.id, u.full_name FROM tickets t JOIN users u ON u.id = t.requester_id;

-- aggregate: WHERE filters rows BEFORE grouping, HAVING filters groups AFTER
SELECT status, count(*) FROM tickets GROUP BY status HAVING count(*) > 5;

-- CTE: name your steps
WITH busy AS (SELECT assignee_id, count(*) n FROM tickets GROUP BY assignee_id)
SELECT * FROM busy WHERE n > 10;

-- window function: calculate across rows, keep every row
SELECT id, priority, rank() OVER (PARTITION BY assignee_id ORDER BY created_at) FROM tickets;

-- conditional counts (great for dashboards)
SELECT count(*) FILTER (WHERE priority = 'urgent') AS urgent FROM tickets;

-- upsert
INSERT INTO page_views (page, views) VALUES ('/', 1)
ON CONFLICT (page) DO UPDATE SET views = page_views.views + 1;
```

## Indexes: the book's index

Without an index Postgres reads **every row** (`Seq Scan`). With one it jumps straight there. Always verify with `EXPLAIN (ANALYZE)`:

```
Seq Scan on events   Filter: (user_id = 1234)   Execution Time: 8.3 ms     -- 200k rows, no index
Bitmap Index Scan on ix_events_user             Execution Time: 0.3 ms     -- after CREATE INDEX
```
| Rule | Why |
|---|---|
| Index columns you **filter, join, or sort** on | that's what indexes accelerate |
| **Foreign keys** deserve an index | joins and `ON DELETE` checks use them |
| Composite `(a, b)` serves `WHERE a` and `WHERE a AND b`, not `WHERE b` alone | left-most prefix rule |
| Every index slows writes and costs disk | don't index everything |
| `GIN` for JSONB / full-text / arrays | different data, different index type |
| Low-selectivity columns (e.g. boolean) rarely benefit | most rows match anyway |

## Transactions & ACID
A transaction groups statements into **all-or-nothing**.
* **A**tomic: all succeed or none. **C**onsistent: constraints always hold. **I**solated: others don't see half-done work. **D**urable: committed = survives a crash.

Default isolation is `READ COMMITTED`: you see only **committed** data from others. Notebook 02 proves it with two connections.

## PostgreSQL superpowers used in TeamDesk
| Feature | Where | Benefit |
|---|---|---|
| **Generated column** `search_vector` | `tickets` | database keeps full-text vector in sync automatically |
| **Full-text search** (`@@`, `plainto_tsquery`) + **GIN index** | `GET /tickets?q=` | stemming ("printers" finds "printer"), ranking, no extra search engine |
| **JSONB** `details` | `audit_logs` | flexible change records you can still query (`details @> '{...}'`) |
| **Composite index** `(status, priority)` | `tickets` | fast dashboards |
| `ON DELETE RESTRICT / SET NULL / CASCADE` | FKs | data integrity decided by the database |

## Best practices
1. **Let the database enforce rules** (NOT NULL, UNIQUE, CHECK, FK), then handle the errors in code.
2. Use `TIMESTAMPTZ` and store **UTC**.
3. Never build SQL with f-strings. **Bind parameters** (`:name`) always (prevents SQL injection).
4. Don't `SELECT *` in application code; name columns.
5. Add indexes based on **real queries** (`EXPLAIN ANALYZE`), not guesses.
6. Change schemas with **migrations**, never by hand on a shared database.
7. Use a **least-privilege** DB user for the app (no `DROP`, no superuser).
8. Backups you have **restored at least once** are the only real backups.

## Common mistakes
| Mistake | Fix |
|---|---|
| `FLOAT` for money | `NUMERIC` |
| "Check if exists, then insert" in code | `UNIQUE` constraint + handle `IntegrityError` |
| `OFFSET 1000000` pagination | keyset pagination (`WHERE id < :last_id ORDER BY id DESC LIMIT 20`) |
| Forgetting an index on a foreign key | add it |
| Long transactions holding locks | keep transactions short; no network calls inside them |
| `LIKE '%word%'` for search | full-text search or `pg_trgm` |

## Useful `psql` commands
```bash
docker compose exec db psql -U teamdesk -d teamdesk     # (make psql)
\dt                list tables        \d tickets      describe a table
\di                list indexes       \x              toggle expanded output
\timing            show query times   \q              quit
```

## Practice
* Write the query: *"top 3 agents by number of resolved tickets this week"* (join + group + order + limit).
* Prove the benefit of `ix_tickets_status_priority` with `EXPLAIN ANALYZE`, then `DROP INDEX` it and compare.
* Try to insert a ticket with `status = 'banana'`. Which layer rejects it first, and which would catch it if the other didn't?
