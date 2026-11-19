# Pydantic: check data once, at the door

**In one sentence:** Pydantic turns *untrusted* data (JSON, forms, env vars, DB rows) into *typed, validated* Python objects, or tells you exactly what is wrong.
**Hands-on:** notebook `01_pydantic_foundations` · **Real code:** `backend/app/schemas/`, `backend/app/core/config.py`, `frontend/models.py`

## Mental model
Think of a **bouncer**. Data arrives at the edge of your program, the bouncer checks it once, fixes small things (`"42"` → `42`), and throws out the rest.
Inside the building nobody re-checks: everything is already trusted. This is *"parse, don't validate"*.

## The 5-minute tour

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=50)
    is_active: bool = True               # default => optional

User(id="42", name="Ada")                # ✅ id coerced to 42
User(id="abc", name="")                  # ❌ ValidationError listing BOTH problems
```

| Feature | Example | Use it for |
|---|---|---|
| **Type hints are rules** | `age: int` | basic correctness |
| **Constraints** | `Field(ge=0, le=120)`, `StringConstraints(strip_whitespace=True)` | length, range, regex |
| **Reusable types** | `Title = Annotated[str, StringConstraints(min_length=3)]` | define once, use everywhere |
| **Validators** | `@field_validator`, `@model_validator` | custom or cross-field rules |
| **Defaults** | `Field(default_factory=list)` | anything mutable or computed per object |
| **Nesting** | `addresses: list[Address]` | structured JSON |
| **Enums / Literal** | `status: TicketStatus` | closed lists of values |
| **Serialization** | `model_dump()`, `model_dump_json()` | output; `exclude_unset=True` for PATCH |
| **`from_attributes`** | `UserOut.model_validate(db_row)` | build from ORM objects |
| **Generics** | `Page[Ticket]` | reusable envelopes |
| **Settings** | `BaseSettings` | config from environment variables |

## Validators in two minutes

```python
class Booking(BaseModel):
    start: date
    end: date

    @field_validator("tags", mode="before")      # BEFORE: raw input. Allow "a,b" as well as ["a","b"]
    @classmethod
    def split(cls, v): return v.split(",") if isinstance(v, str) else v

    @model_validator(mode="after")               # AFTER: typed values. Rules involving several fields
    def order(self):
        if self.end <= self.start: raise ValueError("end must be after start")
        return self
```
Raise `ValueError` (or `AssertionError`); Pydantic turns it into a nicely located error message.

## In TeamDesk

* **Input vs output models are separate.** `UserCreate` (has `password`, no `role`) → `UserRead` (no password). The model you receive is never the model you send.
* **`TicketUpdate` for PATCH** uses `model_fields_set` and `exclude_unset=True` so "field not sent" ≠ "set to null". It also rejects `{}` and explicit `null`s.
* **`TicketFilters`** validates the whole query string as one model; `extra="forbid"` turns a typo (`?stauts=open`) into a `422` instead of silently returning everything.
* **`Page[T]`** is one generic model for every list endpoint.
* **`Settings`** reads env vars and **refuses to start** in `production` with the default secret key (a `model_validator`).
* **`SecretStr`** hides secrets in logs and reprs.
* **Frontend** has its *own* models, validating API responses, so a breaking API change fails loudly in one place.

## Best practices
1. **Separate models for create / update / read.** Never reuse your DB model as your API model.
2. Put constraints on the **type** (`Annotated`), not scattered through code.
3. Validate **strictly on input**, but be lenient on output (`email: str`, not `EmailStr`, on `UserRead`). Old rows must never break a response.
4. Use `exclude_unset=True` for PATCH; `extra="forbid"` where silent ignoring is risky.
5. Use `default_factory` for lists/dicts/datetimes.
6. Use `SecretStr` for passwords and tokens.
7. Prefer `StrEnum`/`Literal` over magic strings.
8. Keep validators **pure**: no database calls or network. Do that in the service layer.

## Common mistakes
| Mistake | Why it bites |
|---|---|
| `x: int \| None` and thinking it's optional | It's still **required** unless it has a default (`= None`). |
| One model for DB + API | Leaks fields (hashes), couples API to schema. |
| Forgetting `from_attributes=True` | `model_validate(orm_obj)` fails with "Input should be a valid dictionary". |
| `model_construct()` on user data | Skips validation entirely. Only for already-validated data. |
| Heavy work in validators | Slows every request; hides business logic. |
| `Optional[...]` everywhere | Hides real "must exist" rules. |

## Practice
* Add `due_date: date | None` to `TicketCreate` and reject dates in the past (`field_validator`).
* Write `OrderOut` with a `computed_field` for `total`.
* Break the settings: set `ENVIRONMENT=production` and start the API; read the error.
