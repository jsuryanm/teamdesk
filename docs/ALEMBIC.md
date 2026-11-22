# Alembic: database migrations explained from zero

**In one sentence:** Alembic is *version control (like git) for your database structure*. Every change to a table, column or index is a small numbered script that can be applied (`upgrade`) or undone (`downgrade`).

**Hands-on:** notebook `03_sqlalchemy_and_alembic` (last sections) · **Real files:** `backend/alembic.ini`, `backend/alembic/`

---

## 1. The problem Alembic solves

Your code changes often. Your **database** has real data in it, so you can't just delete it and start over.

Imagine you add `due_date` to the `Ticket` model:

```python
class Ticket(Base):
    ...
    due_date: Mapped[date | None]      # NEW
```

The Python file now says the column exists, but **the PostgreSQL table doesn't have it yet**. The next query fails with `column tickets.due_date does not exist`.

You could type `ALTER TABLE tickets ADD COLUMN due_date date;` by hand, but then:
* your teammate's database doesn't have it,
* the staging server doesn't have it,
* production doesn't have it, and nobody remembers *what* was run *when*.

**Migrations fix this.** The change is written once, as a file in git, and every environment runs the same file:

```
developer laptop ──┐
teammate laptop ───┼── all run the SAME migration files, in the SAME order ──► identical schemas
CI database ───────┤
production ────────┘
```

> **SQLAlchemy vs Alembic:** SQLAlchemy *describes* the schema (your model classes). Alembic *changes* a real database to match it. They are made by the same author and work together.

---

## 2. The mental model: a chain of steps

Each migration has an **ID** and says which migration comes **before** it. Together they form a chain, like git commits:

```
(empty database) ──► 0001 initial schema ──► 3f9a1c2b7d10 add due_date ──► 8b2e4d6a9c01 add index  ◄── "head" (newest)
```

* **`head`** = the newest migration.
* The database remembers where it is: Alembic keeps **one table** called `alembic_version` with **one row** containing the current revision ID.
* `alembic upgrade head` means *"run every migration after my current position, up to the newest."*

```bash
docker compose exec db psql -U teamdesk -d teamdesk -c "select * from alembic_version;"
#  version_num
# -------------
#  0001
```

---

## 3. What is in the `alembic/` folder

```
backend/
├── alembic.ini                 settings for the alembic command (where scripts live, file naming, log format)
└── alembic/
    ├── env.py                  the "glue": connects Alembic to YOUR database URL and YOUR models
    ├── script.py.mako          the template used to create each new migration file
    └── versions/
        └── 20261119_0001_initial_schema.py     one file per migration
```

| File | What it does | Do you edit it? |
|---|---|---|
| `alembic.ini` | `script_location`, the file name pattern (`date_revision_slug`), logging | rarely |
| `env.py` | reads `DATABASE_URL` from the app settings, imports all models so `Base.metadata` knows every table, runs migrations | once, at setup |
| `script.py.mako` | boilerplate for new files | almost never |
| `versions/*.py` | **the migrations** | yes: review every generated file |

### What `env.py` does in TeamDesk (4 important lines)

```python
import backend.app.models                                   # 1. load every model, so all tables are registered
config.set_main_option("sqlalchemy.url", get_settings().database_url)   # 2. same URL as the app (from .env / environment)
target_metadata = Base.metadata                     # 3. "what the database SHOULD look like"
connectable = engine_from_config(..., poolclass=pool.NullPool)           # 4. connect, run migrations in a transaction
```

> **The API is async, but Alembic is not.** Alembic uses a normal *synchronous* connection from the **same URL** (`postgresql+psycopg://...`). Migrations run once, before the server starts, so there is nothing to gain from async here.

---

## 4. Anatomy of one migration

Open `backend/alembic/versions/20261119_0001_initial_schema.py`. Every migration has the same shape:

```python
revision = "0001"            # this migration's ID
down_revision = None         # the migration BEFORE it (None = the very first)

def upgrade() -> None:       # how to move FORWARD
    op.create_table("tags", sa.Column("id", sa.Integer(), nullable=False), ...)
    op.create_index("ix_tickets_search_vector", "tickets", ["search_vector"], postgresql_using="gin")

def downgrade() -> None:     # how to move BACK (the exact reverse, in reverse order)
    op.drop_index("ix_tickets_search_vector", table_name="tickets")
    op.drop_table("tags")
```

`op` is Alembic's toolbox. The ones you will use most:

| Operation | SQL it produces |
|---|---|
| `op.create_table("t", sa.Column(...))` | `CREATE TABLE t (...)` |
| `op.drop_table("t")` | `DROP TABLE t` |
| `op.add_column("t", sa.Column("c", sa.Date(), nullable=True))` | `ALTER TABLE t ADD COLUMN c date` |
| `op.drop_column("t", "c")` | `ALTER TABLE t DROP COLUMN c` |
| `op.alter_column("t", "c", nullable=False)` | `ALTER TABLE t ALTER COLUMN c SET NOT NULL` |
| `op.alter_column("t", "old", new_column_name="new")` | `ALTER TABLE t RENAME COLUMN old TO new` |
| `op.create_index("ix_name", "t", ["c"])` | `CREATE INDEX ix_name ON t (c)` |
| `op.create_foreign_key(...)`, `op.create_unique_constraint(...)` | constraints |
| `op.execute("UPDATE ...")` | any raw SQL (data fixes) |

---

## 5. The everyday workflow (follow this every time)

Example: add an optional due date to tickets.

**Step 1: Change the model** (`backend/app/models/ticket.py`)

```python
from datetime import date
...
due_date: Mapped[date | None] = mapped_column(default=None)
```

**Step 2: Make Alembic write the migration for you** (it compares the models with the real database)

```bash
cd backend
uv run alembic revision --autogenerate -m "add ticket due date"
```
A new file appears in `alembic/versions/`, named like `20261120_3f9a1c2b7d10_add_ticket_due_date.py`.
(The ID is a random hex string; TeamDesk's first migration was given the readable ID `0001`.)

**Step 3: READ the generated file.** Never skip this. It should look like:

```python
def upgrade() -> None:
    op.add_column("tickets", sa.Column("due_date", sa.Date(), nullable=True))

def downgrade() -> None:
    op.drop_column("tickets", "due_date")
```
Ask: *Is this exactly what I meant? Is anything missing? Could it lose data?*

**Step 4: Apply it**

```bash
uv run alembic upgrade head
```

**Step 5: Prove it is consistent**

```bash
uv run alembic check          # "No new upgrade operations detected." = models and database agree
```

**Step 6: Prove it is reversible** (do this once on your laptop, never on production)

```bash
uv run alembic downgrade -1   # undo the newest migration
uv run alembic upgrade head   # redo it
```

**Step 7: Commit the model change and the migration file together** in the same pull request.

> Shortcut with the Makefile: `make revision m="add ticket due date"` then `make migrate`.

---

## 6. Command cheat sheet

Run from `backend/`. With uv, prefix with `uv run` (no need to activate a virtual environment).

| Command | Meaning |
|---|---|
| `alembic upgrade head` | apply all pending migrations |
| `alembic upgrade +1` | apply just the next one |
| `alembic downgrade -1` | undo the newest applied migration |
| `alembic downgrade base` | undo everything (empty database; **destroys data**) |
| `alembic current` | which revision is this database at? |
| `alembic history --verbose` | the whole chain |
| `alembic heads` | the newest revision(s). **Should print exactly one.** |
| `alembic check` | fail if the models differ from the migrated database (used in CI) |
| `alembic revision -m "msg"` | create an **empty** migration (you write it, e.g. for data changes) |
| `alembic revision --autogenerate -m "msg"` | create a migration from model changes |
| `alembic upgrade head --sql` | print the SQL instead of running it (great for review / DBAs) |
| `alembic stamp head` | tell Alembic "this database is already at head" **without** running anything |

---

## 7. What autogenerate can and cannot do

Autogenerate *compares* two things: your models vs the live database. It is a **draft writer**, not a mind reader.

| It detects | It can NOT detect (you must check or write by hand) |
|---|---|
| new / removed tables and columns | **renames**: a renamed column looks like "drop old + add new" and would **delete the data** |
| nullable changes, type changes (we enable `compare_type=True`) | **data changes**: filling a new column for existing rows |
| new / removed indexes and unique constraints | some constraint expressions and server-side defaults (always review) |
| foreign keys | changes inside a `CHECK` or a PostgreSQL function/trigger |

### The rename trap (important)

You rename `due_date` → `deadline` in the model. Autogenerate writes:

```python
op.add_column("tickets", sa.Column("deadline", sa.Date()))
op.drop_column("tickets", "due_date")        # DATA LOST
```
Edit the file by hand to preserve the data:

```python
def upgrade() -> None:
    op.alter_column("tickets", "due_date", new_column_name="deadline")

def downgrade() -> None:
    op.alter_column("tickets", "deadline", new_column_name="due_date")
```

### Data migrations (changing rows, not structure)

Create an empty migration and write the SQL yourself:

```bash
uv run alembic revision -m "backfill due dates"
```
```python
def upgrade() -> None:
    op.execute("UPDATE tickets SET due_date = created_at::date + 7 WHERE due_date IS NULL")

def downgrade() -> None:
    pass      # not reversible: say so honestly (or raise NotImplementedError)
```
Keep **structure** and **data** changes in **separate** migrations.

---

## 8. Changing a table that already has data (safe patterns)

Adding a `NOT NULL` column to a table with rows fails, because existing rows have no value. Do it in **three small steps** (ideally three migrations, or one migration with three operations):

```python
def upgrade() -> None:
    op.add_column("tickets", sa.Column("severity", sa.String(20), nullable=True))   # 1. allow NULL first
    op.execute("UPDATE tickets SET severity = 'normal'")                              # 2. fill existing rows
    op.alter_column("tickets", "severity", nullable=False)                            # 3. now enforce it
```

### Expand → migrate → contract (for zero-downtime deploys)
When old and new application versions run at the same time during a deploy, never make a change the *old* code can't survive:

1. **Expand:** add the new column/table (old code ignores it).
2. **Migrate:** deploy code that writes to both, and backfill old rows.
3. **Contract:** in a *later* release, remove the old column.

Renaming a column in a single step breaks the old code instantly; use the three steps above for live systems.

### Large tables
* `CREATE INDEX` locks writes on the table. On big tables use `CREATE INDEX CONCURRENTLY` (needs `with op.get_context().autocommit_block():`).
* Rewriting a huge column type can take minutes: test on a copy of production data first.

---

## 9. Team rules (these prevent 90 % of pain)

1. **Never edit a migration that has already run anywhere** (teammates, CI, staging, production). Write a *new* migration instead. Editing history makes databases disagree silently.
2. **One migration per logical change**, with a clear message (`add ticket due date`, not `update`).
3. **Always review autogenerated files.** Treat them as a draft.
4. **Always write `downgrade()`** (or say clearly that it isn't possible).
5. **Commit the migration with the model change** in the same pull request.
6. **Keep one `head`.** If two branches both added a migration, you get two heads. Fix with `alembic merge heads -m "merge"`.
7. **Never use `Base.metadata.create_all()` outside tests.** It bypasses version tracking (the test suite uses it only because tests build a throw-away database).
8. **Take a backup before running migrations on production.**
9. **CI runs `alembic upgrade head` and `alembic check`** (see `.github/workflows/ci.yml`), so a forgotten migration fails the build, not production.

### Why constraint names matter
`backend/app/db/base.py` defines a **naming convention** (`pk_tags`, `uq_tags_name`, `fk_tickets_requester_id_users`, ...). Without it PostgreSQL invents names, and then `op.drop_constraint(...)` can't refer to them reliably. Stable names make future migrations simple.

---

## 10. How TeamDesk applies migrations

| Where | How |
|---|---|
| **Docker Compose** | `backend/docker-entrypoint.sh` runs `alembic upgrade head` **before** starting the API (then optionally seeds demo data). Postgres is already *healthy* because of `depends_on: condition: service_healthy`. |
| **Local development** | `make migrate` (or `cd backend && uv run alembic upgrade head`) |
| **CI** | upgrade, then `alembic check`, then tests |
| **Production** | run `alembic upgrade head` as a **one-off release job** before rolling out new containers. If 5 replicas all migrate at the same moment on start-up, they race. The entrypoint approach is fine for one instance. |

---

## 11. Troubleshooting

| Message / symptom | Meaning | Fix |
|---|---|---|
| `Target database is not up to date.` (on `--autogenerate`) | the database is behind `head` | `alembic upgrade head`, then try again |
| `relation "users" already exists` | the tables were created some other way (e.g. `create_all`) | start fresh (`docker compose down -v`), or if the schema is truly identical, `alembic stamp head` |
| `Can't locate revision identified by '...'` | the database points to a migration file you don't have | `git pull` to get the missing file, or check you are using the right database |
| `Multiple head revisions are present` | two migrations share the same parent | `alembic merge heads -m "merge"` |
| Autogenerate produced an **empty** migration | models and database already agree, or the model isn't imported | check `app/models/__init__.py` imports your model |
| Autogenerate wants to **drop** something you did not remove | the database has objects the models don't know about | read carefully; delete that line if it is unrelated |
| `column "x" does not exist` at runtime | model changed but migration not applied | `alembic upgrade head` |
| `could not connect to server` | database not running or wrong URL | `docker compose up -d db`; check `DATABASE_URL` |

---

## 12. Practice (in order)

1. Run `uv run alembic current`, `history`, `heads`. Find the `alembic_version` row with `psql`.
2. Run `uv run alembic upgrade head --sql | head -60` and match each statement to the model.
3. Add `due_date` to `Ticket` (section 5), generate, read, apply, `check`, downgrade, upgrade.
4. Rename that column to `deadline` **correctly** (section 7), without losing data. Verify with a row inserted before the migration.
5. Add a `NOT NULL` column `severity` with a default using the three-step pattern (section 8).
6. Create two migrations on two git branches, merge them, and resolve the **two heads** problem.

**Next:** [03-postgresql.md](03-postgresql.md) for the database features the migrations create, or [SETUP.md](SETUP.md) to run it all.
