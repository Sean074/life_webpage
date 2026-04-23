# Auth Standard

This document defines the authorisation patterns for this project. All new routes must follow these conventions.

---

## Roles

| Role | Access |
|------|--------|
| `admin` | All restricted pages + all write/mutate operations |
| `user` | All restricted pages, read-only |
| *(unauthenticated)* | Public pages only |

Roles are stored in the `users` table (`role TEXT CHECK(role IN ('admin', 'user'))`). There is no self-registration — users are created via `scripts/create_user.py`.

---

## Session Mechanism

Sessions use a signed cookie (`itsdangerous.TimestampSigner`). The cookie stores a signed user ID, not the full user object. On each request, `get_current_user` verifies the signature and fetches the user row from the database.

- Cookie name: `session`
- Max age: 7 days
- Flags: `httponly=True`, `samesite="lax"`
- Secret: `SECRET_KEY` env var (required in production — never use the default)

---

## Core Functions — `app/auth.py`

| Function | Purpose |
|----------|---------|
| `get_current_user(request)` | Returns `{"id", "username", "role"}` or `None`. Use when auth is optional (public pages that show different UI for logged-in users). |
| `require_auth` | FastAPI `Depends()`. Returns the user dict or redirects to `/login` (307). Use on all restricted-page GET routes. |
| `require_admin` | FastAPI `Depends(require_auth)`. Returns the user dict or returns 403. Use on all write/mutate routes. |
| `create_session(response, user_id)` | Sets the signed session cookie on a response. Call after successful login. |
| `clear_session(response)` | Deletes the session cookie. Call on logout. |
| `hash_password(plain)` | Returns a bcrypt hash. Use when creating/updating users. |
| `verify_password(plain, hashed)` | Returns bool. Use during login credential check. |

---

## Applying Auth to Routes

### Restricted page (any logged-in user)

```python
from fastapi import Depends
from app.auth import require_auth

@router.get("/wealth")
async def wealth(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse("wealth/index.html", {
        "request": request,
        "user": user,
        "active": "wealth",
    })
```

### Admin-only write operation

```python
from app.auth import require_admin

@router.post("/blog/new")
async def blog_new(request: Request, ..., user: dict = Depends(require_admin)):
    ...
```

### Public page with optional user context

```python
from app.auth import get_current_user

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": get_current_user(request),
        "active": "home",
    })
```

**Never** pass `"user": True` or `"user": None` as a hardcoded value — always call `get_current_user` or receive `user` from a dependency.

---

## Route Classification

| Route type | Dependency | Examples |
|------------|-----------|---------|
| Public read | None (`get_current_user` for nav context) | `GET /`, `GET /blog`, `GET /gallery` |
| Restricted read | `require_auth` | `GET /library`, `GET /expenses`, `GET /wealth`, `GET /health` |
| Admin write | `require_admin` | `POST /library/sync`, `POST /library/items/{id}/edit`, `POST /blog/new`, `POST /gallery/upload` |
| Auth endpoints | Neither | `GET /login`, `POST /login`, `GET /logout` |

---

## CSRF Protection

All POST forms use the double-submit cookie pattern:

1. On `GET /login`, a random token is generated with `secrets.token_hex(16)`, embedded as a hidden form field, and also set as a `csrf_token` cookie (`httponly=False` so JS can read it if needed).
2. On `POST /login`, the form field value and cookie value are compared using `secrets.compare_digest`. Mismatch → 400.

Apply this same pattern to any new POST form that is not protected by `require_admin` (admin routes are already behind auth, which provides session-level protection, but adding CSRF to them is harmless and preferred).

---

## Rate Limiting on Login

`POST /login` tracks failures per IP in a module-level dict. After 5 failures within 60 seconds the endpoint returns 429 and refuses further attempts until the window expires. This is in-process only — it resets on server restart and does not persist across workers.

Constants in `app/routes/auth_routes.py`:

```python
_RATE_WINDOW = 60   # seconds
_RATE_LIMIT = 5     # failures before lockout
```

---

## Template Guards

Pass the full `user` dict (or `None`) to every template context. In templates:

```html
{% if user %}
  <!-- shown to any logged-in user -->
{% endif %}

{% if user and user.role == 'admin' %}
  <!-- shown only to admins: edit buttons, new post links, upload forms -->
{% endif %}
```

Template guards are UI-only. They must not replace server-side `require_admin` checks — a user-role user could craft a raw POST request without the UI.

---

## Adding a New User

```bash
python scripts/create_user.py --username alice --role user
# or
python scripts/create_user.py --username sean --role admin
```

Run from the project root with the venv active.

---

## Environment

`.env` must contain:

```
SECRET_KEY=<long random string>
```

Generate one with: `python -c "import secrets; print(secrets.token_hex(32))"`

Never commit `.env`. The `.env.example` file documents required keys without values.
