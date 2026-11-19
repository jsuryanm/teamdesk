# Streamlit: a web UI in pure Python

**In one sentence:** Streamlit turns a Python script into an interactive web page. The **whole script re-runs from top to bottom** every time the user touches a widget.
**Hands-on:** notebook `07_streamlit_and_testing` · **Real code:** `frontend/`

## Mental model
A **spreadsheet that recalculates**. Widgets are cells holding values; any change recalculates the sheet. Once you accept that *"everything re-runs"*, you know why state, caching and forms exist.

```python
import streamlit as st
n = st.slider("Pick a number", 0, 10)      # returns the current value on every run
st.write(n * n)                            # changes whenever the slider moves
```

## The 4 ideas that matter

| Idea | Problem it solves | Code |
|---|---|---|
| **Rerun model** | UI = a function of state | just write top-to-bottom code |
| **`st.session_state`** | variables reset on each run | `st.session_state["token"]` (per browser tab) |
| **Caching** | expensive work repeats | `@st.cache_data(ttl=30)` for data, `@st.cache_resource` for objects (DB pools, models) |
| **Forms** | each keystroke triggers a rerun | `with st.form(...):` + `st.form_submit_button` |

```python
if "count" not in st.session_state:           # survives reruns
    st.session_state.count = 0
if st.button("Add"):
    st.session_state.count += 1
st.write(st.session_state.count)
```

## Structure of the TeamDesk UI

```
frontend/
├── app.py            entry: page config, auth gate, st.navigation, sidebar (user + sign out)
├── views/            one file per page: login · dashboard · tickets · new_ticket · admin_users
├── ticket_detail.py  reusable panel (a module, not a page)
├── api_client.py     the ONLY place that speaks HTTP (typed, returns Pydantic objects)
├── models.py         Pydantic models for API responses (own copy, not imported from backend)
├── state.py          login/logout, get_client(), api_errors() context manager
├── observability.py  Logfire setup (once, via cache_resource)
└── config.py         settings (API_URL)
```

### Patterns worth copying
1. **Auth gate in `app.py`:** `if not is_logged_in(): navigation([login]) else: navigation([...pages])`. Unauthenticated users never even *see* the other pages.
2. **One API client class.** Pages call `client.list_tickets(...)` and get typed objects. If the API contract changes, you fix **one** file.
3. **`with api_errors():`** turns `ApiError` into a friendly `st.error` (with the request id) and, on `401`, logs the user out. No stack traces in the UI.
4. **Shared connection pool.** A module-level `httpx.Client`; creating a new client on every rerun leaks connections.
5. **Cache keyed by user.** `load_stats(token)` is cached for 30 s; the token is an *argument*, so users never see each other's data.
6. **List ↔ detail without extra pages:** `st.session_state["selected_ticket"]` switches `tickets.py` between table and detail mode.
7. **Filters reset the page:** `on_change=reset_page` callback sets page = 1.
8. **Server-side validation is shown, not duplicated.** The UI doesn't re-implement "title ≥ 3 chars"; it displays the API's `422` messages.
9. **Parallel fetching.** The ticket page needs 4 API calls; `client.ticket_bundle()` makes them concurrently (async httpx on one persistent background event loop, shared connection pool, trace context copied). See [14](14-async-and-parallelism.md).

### Security notes
* The JWT lives in **server-side** `session_state` (never in the URL or browser storage).
* Role checks in the UI (`if role == "admin"`) are **cosmetic**; the API enforces them.
* Never trust anything *only* because the UI hid the button.

## Widgets cheat sheet
| Need | Widget |
|---|---|
| text / long text / password | `text_input`, `text_area`, `text_input(type="password")` |
| numbers / sliders | `number_input`, `slider`, `select_slider` |
| choices | `selectbox`, `multiselect`, `radio`, `toggle`, `checkbox` |
| layout | `columns`, `tabs`, `expander`, `container(border=True)`, `sidebar` |
| data | `dataframe` (selectable rows), `metric`, `bar_chart`, `line_chart` |
| feedback | `success`, `info`, `warning`, `error`, `toast`, `spinner` |
| control flow | `rerun()`, `stop()`, `switch_page()`, `page_link()` |
| chat-like | `chat_message`, `chat_input` (used for comments) |

## Testing a Streamlit app
`AppTest` runs the script headlessly: no browser.

```python
at = AppTest.from_file("app.py").run()
at.text_input[0].input("ada@example.com"); at.text_input[1].input("right")
at.button[0].click().run()
assert at.session_state["token"] == "fake-token"
assert {m.label: m.value for m in at.metric}["Total"] == "7"
```
Swap the real API client for a fake (`monkeypatch.setattr(state, "TeamDeskClient", FakeClient)`) and the UI is testable without a backend (`frontend/tests/test_app.py`).

## Common mistakes
| Mistake | Effect |
|---|---|
| Plain variable for counters/flags | resets every run → use `session_state` |
| Heavy work outside a cache | page feels slow on every click |
| New `httpx.Client` per rerun | connection leak |
| Cache without the user as a key | data leaks between users |
| Forgetting `st.rerun()` after changing state | page shows stale data until the next interaction |
| Hard-coding secrets in the app | use env vars or `.streamlit/secrets.toml` (never commit it) |
| Business rules in the UI | duplicated and bypassable; keep them in the API |

## When to choose something else
Streamlit is perfect for internal tools, dashboards and prototypes. For public, highly-custom, or offline-capable UIs use a React/Vue front end against the **same API**. Nothing in the backend would change.

## Practice
* Add a **"My tickets"** toggle on the Tickets page for agents (`requester_id = me`).
* Add a *CSV download* button (`st.download_button`) for the current filter.
* Add an `AppTest` that opens the Tickets page and asserts the table shows the fake tickets.
