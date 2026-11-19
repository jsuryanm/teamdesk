# Authentication & Security

**In one sentence:** *Authentication* proves **who** you are; *authorization* decides **what** you may do; most breaches come from mixing them up or forgetting one.
**Hands-on:** notebook `05_auth_jwt_and_rbac` · **Real code:** `backend/app/core/security.py`, `backend/app/api/deps.py`, `backend/app/services/tickets.py`

## Mental model
A **concert**: your *ticket* (JWT) proves you bought entry (authentication). The *wristband colour* (role) decides which areas you can enter (authorization). And you still can't sit in someone else's *numbered seat* (ownership).

## 1. Passwords
* Store **only a slow, salted hash**: TeamDesk uses **Argon2id** (`pwdlib`). ~116 ms per guess (notebook 05 measures it) vs. 0.0004 ms for SHA-256.
* Same password → different hash each time (random salt).
* Never log, return, or email passwords or hashes. `UserRead` has no password field at all.
* Unknown email and wrong password take the **same time and show the same message** (`DUMMY_HASH`) so attackers can't discover which emails exist.

## 2. JWT (JSON Web Token)
`header.payload.signature`, three Base64 parts.
* The **signature** (HMAC with `SECRET_KEY`) proves the server issued it; any edit breaks it.
* The payload is **readable by anyone**: signed, **not encrypted**. Never put secrets in it.
* TeamDesk's payload: `sub` (user id), `iat`, `exp`, `type`. **No role.**
* Always decode with `algorithms=[...]` pinned (blocks the `alg: none` trick).
* Tokens expire (`ACCESS_TOKEN_EXPIRE_MINUTES`). Short expiry limits damage if one leaks.

### The login flow (OAuth2 password flow)
```
POST /api/v1/auth/token   (form: username=<email>, password=...)
  → 200 {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600}
GET  /api/v1/tickets      Authorization: Bearer eyJ...
```
`OAuth2PasswordBearer` makes Swagger's **Authorize** button work automatically.

## 3. Authorization: three layers
| Layer | Question | TeamDesk implementation |
|---|---|---|
| **Role (RBAC)** | May *agents* do this? | `require_roles(...)` dependency → `403` |
| **Ownership** | May *this user* touch *this row*? | `_scope(user)` adds `WHERE requester_id = :me` for requesters |
| **State** | Is it allowed *right now*? | status state machine, "only open tickets can be edited" |

**Always re-load the user from the database on each request.** A demoted or deactivated user loses power immediately, even with an old, still-valid token (tested in `test_auth.py`).

### 404 instead of 403 for other people's rows
`GET /tickets/17` for someone else's ticket returns **404**. A 403 would confirm the ticket exists (information leak). Attackers can't enumerate IDs.

### IDOR and mass assignment, the two classics
* **IDOR** (Insecure Direct Object Reference): forgetting the ownership check; `/orders/17` works for anyone logged in. Prevent by putting the scope **inside the query**.
* **Mass assignment**: letting clients set fields they shouldn't. `UserCreate` has **no `role` field**, so `{"role": "admin"}` in sign-up is ignored. Admins use a separate `UserCreateByAdmin`.

## 4. Other protections already in the code
| Threat | Defence |
|---|---|
| SQL injection | ORM / bound parameters only |
| Oversized or malformed input | Pydantic constraints (`max_length`, enums) |
| Secrets in logs | `SecretStr`, Logfire scrubbing, never logging bodies of auth calls |
| Default secret in production | `Settings` **refuses to start** |
| Cross-site requests from other origins | CORS limited to the UI origin |
| Container compromise | non-root user in Docker |
| Race on "email taken" | `UNIQUE` constraint + `IntegrityError` handling |

## 5. What a real deployment still needs
- [ ] **HTTPS** everywhere (TLS at a reverse proxy / load balancer)
- [ ] **Refresh tokens** (short access token + revocable long-lived refresh token) or sessions
- [ ] **Rate limiting** and lockout on login (e.g. `slowapi`, API gateway, WAF)
- [ ] **MFA** for staff · **SSO via OIDC** (Entra ID, Okta, Auth0, Keycloak) for enterprise customers: delegate password handling entirely
- [ ] **Secrets manager** (not `.env` files) and a **rotation** plan for `SECRET_KEY`
- [ ] Least-privilege **database user**; DB not exposed publicly (remove the `5432:5432` port mapping)
- [ ] Security headers, dependency scanning (`pip-audit`, Dependabot), image scanning
- [ ] Audit logging (TeamDesk has the foundation: `audit_logs`) and alerting on odd patterns

## Best practices checklist
1. Deny by default; add permission only where needed.
2. Check **role + ownership + state** on the server, always. UI checks are only friendliness.
3. Use well-tested libraries; never invent crypto.
4. Same error for "bad user" and "bad password".
5. Log security events (login failures, permission denials) **without secrets**.
6. Keep tokens out of URLs (they end up in logs); use the `Authorization` header.
7. Write a test for **every denial** you implement.

## Common mistakes
| Mistake | Fix |
|---|---|
| Trusting the role inside the token | re-read the user from the DB |
| MD5/SHA for passwords | Argon2id / bcrypt |
| Checking permissions only in the UI | enforce in the API |
| `Access-Control-Allow-Origin: *` with credentials | list exact origins |
| JWT in `localStorage` for a browser SPA | prefer `HttpOnly` cookies; (Streamlit keeps the token in **server-side** session memory) |
| Forgetting `algorithms=` on decode | pin it |

## Practice
* Add `POST /auth/refresh` with refresh tokens stored (hashed) in a table so they can be revoked.
* Add a `failed_logins` counter to `users` and lock the account for 15 minutes after 5 failures. Write the tests first.
* Write a test proving a requester cannot read another requester's **comments**.
