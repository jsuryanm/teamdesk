# Observability with Pydantic Logfire

**In one sentence:** observability means being able to answer *"what is my system doing, and why is it slow or broken?"* from the data it emits, without adding new code first.
**Hands-on:** notebook `06_logfire_observability` · **Real code:** `backend/app/core/observability.py`, `backend/app/main.py`, `frontend/observability.py`

## Mental model
| Thing | Analogy | Example |
|---|---|---|
| **Log** | a diary entry | `ticket created, ticket_id=42` |
| **Span** | a stopwatch around an operation | `POST /tickets` took 38 ms |
| **Trace** | the whole family tree of spans for one request | UI click → API call → 4 SQL queries |
| **Metric** | a number over time | requests per minute |

Logfire is built on **OpenTelemetry** (an open standard), so what you learn transfers to any vendor.

## Structured logging in one minute

```python
logfire.info("order {order_id} placed by {user}", order_id=123, user="ada")   # fields, not just text
with logfire.span("charge card {order_id}", order_id=123):                      # timed, nested
    ...
logfire.exception("could not parse {raw}", raw=value)                          # error + traceback
```
Why `{braces}` + keyword arguments instead of an f-string? An f-string makes one opaque sentence; fields stay **searchable**: *"all errors where `reason = 'card_declined'`"*.

## How TeamDesk wires it (4 lines that matter)

```python
logfire.configure(service_name="teamdesk-api", environment=..., send_to_logfire="if-token-present", distributed_tracing=True)
logfire.instrument_pydantic(record="failure")   # validation failures become logs
logfire.instrument_sqlalchemy(engine=engine)    # every SQL statement becomes a span
logfire.instrument_fastapi(app, excluded_urls="/health")   # every request becomes a span
```
| Setting | Meaning |
|---|---|
| `send_to_logfire="if-token-present"` | no token → console only; token → cloud too. Never crashes without one |
| `distributed_tracing=True` | accept the `traceparent` header sent by the UI, so the trace continues across services |
| `record="failure"` | don't log every successful validation (noise + cost) |
| `excluded_urls="/health"` | keep health probes out of your traces |
| default scrubbing | hides values of keys like `password`, `token`, `secret`, `api_key` |

The **Streamlit** app also configures Logfire (`service_name="teamdesk-ui"`) and calls `logfire.instrument_httpx()`, so every API call carries a trace id.
Result: **one trace shows the click, the API request, and each SQL query**.

### Request IDs
Middleware gives each request an ID (or reuses the caller's), returns it as `X-Request-ID`, and sets it as OpenTelemetry **baggage**, so it is attached to every span and log line of that request.
Error responses include it too. A user can paste it into a support ticket and you find the whole story in one search.

## Seeing the data

| Where | How |
|---|---|
| **Terminal** (always) | `docker compose logs -f backend` or the terminal running uvicorn |
| **Logfire cloud** (optional) | set `LOGFIRE_TOKEN` in `.env`; use **Live**, **Explore** (SQL over your telemetry), **Dashboards**, **Alerts** |

Example Explore query (attribute names depend on the instrumentation; open one record in the UI to see the exact names):
```sql
SELECT start_timestamp, message, duration
FROM records
WHERE attributes->>'http.route' = '/api/v1/tickets' AND duration > 0.3
ORDER BY duration DESC LIMIT 20
```

## What to log (and not)

| ✅ Do | ❌ Don't |
|---|---|
| Business events with IDs: `ticket created`, `ticket_id=42` | `entering function X` noise |
| Spans around units of work: request, job, external call | a span around every tiny function |
| Honest levels: `info` normal, `warn` odd, `error` needs a human | `error` for expected events (a 404 is `info`) |
| Include `request_id`, `user_id`, version, environment | passwords, tokens, full card numbers, personal data |
| Sample in high-volume production (keep errors & slow traces) | store 100% of probes and heartbeats |

> Scrubbing is a **safety net, not a license**. Log **IDs**, not **people**. Anything in a log may be copied into a screenshot or ticket.

## Debugging recipes
| Question | Look for |
|---|---|
| *Why is this endpoint slow?* | the slowest child span: a SQL statement? an external call? |
| *Is it an N+1 problem?* | many identical `SELECT` spans under one request |
| *Why did the UI show an error?* | the `request_id` in the red box → search it |
| *Is the new deploy worse?* | filter by `service_version`, compare p95 durations |
| *Who is hitting 403s?* | `domain error permission_denied` logs grouped by user id |

## Best practices
1. Configure observability **first** (before features); retrofitting is painful.
2. Always set `service_name`, `environment`, `service_version`.
3. Propagate a request/trace id across **every** service boundary.
4. Instrument at the framework level (FastAPI, SQLAlchemy, httpx); add manual spans only for meaningful business steps.
5. Alert on **symptoms** users feel (error rate, latency), not on every internal blip.
6. Keep logs structured; avoid building strings.
7. Test that sensitive keys are scrubbed (see notebook 06 section 9).

## Common mistakes
* Forgetting `logfire.configure()` in scripts (you get a warning and no output; `seed.py` calls it).
* Calling `instrument_pydantic()` *after* defining models (it must come first).
* Logging inside tight loops (cost and noise).
* Putting secrets in span names or attributes with innocent-looking keys (`"data": password` isn't scrubbed by key!).

## Practice
* Trigger a 403 as a requester, copy `request_id` from the response, find it in the terminal logs.
* Add a custom span around the audit write in `services/audit.py` and look at the trace tree.
* Configure `sampling=logfire.SamplingOptions.level_or_duration()` and explain what you'd lose and gain.
