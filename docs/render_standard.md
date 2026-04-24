# Render Deployment Standard

This document defines how this project must be deployed on Render. Follow it exactly — do not invent alternative patterns.

---

## Core Constraints

- The `data/` directory contains SQLite databases and financial CSVs. **None of it is ever committed to git.**
- Render's default filesystem is ephemeral — files written outside a persistent disk are lost on each deploy. Every database and data file must live on the persistent disk.
- The only path exposed to HTTP clients is `app/static/` (as `/static`) and `data/images/` (as `/art`). No other subdirectory of `data/` is ever mounted or served.

---

## Persistent Disk

Provision one persistent disk on the Render service. Mount it at `/data`.

| Setting | Value |
|---------|-------|
| Mount path | `/data` |
| Size | 1 GB (increase if image library grows) |

The application reads `data/` as a relative path in development. In production the working directory is the repo root and `/data` satisfies that relative reference — no code changes are required provided Render's working directory is set to `/` or the repo root.

**On first deploy**, manually upload the database files and `finance.csv` to the disk via the Render shell (`Connect > Shell`):

```bash
# Run once after the disk is attached
ls /data   # verify mount is live
```

Then copy files from your local machine using `scp` or the Render shell's upload feature. The expected layout on disk:

```
/data/
  finance.csv
  expenses.db
  gallery.db
  health.db
  library.db
  wealth.db
  images/        # gallery thumbnails and originals
  expenses/      # bank CSV imports (if any)
```

Do not place any other files in `/data` unless CLAUDE.md explicitly adds them to the schema.

---

## Environment Variables

Set all secrets in the Render dashboard under **Environment → Environment Variables**. Never put secret values in the repo or a committed `.env` file.

| Variable | Required | Notes |
|----------|----------|-------|
| `SECRET_KEY` | Yes | `python -c "import secrets; print(secrets.token_hex(32))"` — generate locally, paste into Render |
| `ENVIRONMENT` | Yes | Set to `production` |

The `.env.example` file in the repo documents keys without values and is the only env-related file that may be committed.

At startup, `app/main.py` calls `load_dotenv()`. In production this is a no-op because no `.env` file exists — all values come from the process environment injected by Render.

---

## Build and Start Commands

In the Render service settings:

| Setting | Value |
|---------|-------|
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2` |

Use exactly 2 workers. The in-process login rate-limiter (`_RATE_LIMIT` / `_RATE_WINDOW` in `auth_routes.py`) is per-worker, so with 2 workers a determined attacker has at most `2 × _RATE_LIMIT` attempts before both workers lock out. Do not raise workers beyond 4 without first replacing the in-process limiter with a shared store.

Do not add `--reload` in production.

---

## What Must Not Be Served Over HTTP

Render does not automatically serve filesystem paths — only what the FastAPI app explicitly mounts is reachable. The current mounts are:

```python
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/art",    StaticFiles(directory="data/images"), name="art")
```

The following must **never** be added as a StaticFiles mount or any other HTTP-accessible route:

- `data/*.db` — SQLite databases
- `data/finance.csv` — financial source data
- `data/expenses/` — raw bank CSV imports
- `data/` root itself

If a new route ever needs to serve a file from `data/`, it must read the file in Python and stream the response with explicit auth (`require_auth` or `require_admin`), not via a blanket `StaticFiles` mount.

---

## HTTPS

Render provides TLS automatically on all services. Do not disable it or add a plain HTTP listener. The session cookie is set with `samesite="lax"` and `httponly=True`; in production it must also be `secure=True`.

Update `app/auth.py` `create_session` to set `secure` based on the environment:

```python
import os

secure = os.getenv("ENVIRONMENT") == "production"

response.set_cookie(
    key="session",
    value=signed,
    max_age=7 * 24 * 3600,
    httponly=True,
    samesite="lax",
    secure=secure,
)
```

This change is required before the first production deploy.

---

## Deploy Checklist

Run through this list for every deploy.

**Before pushing:**
- [ ] `data/` is listed in `.gitignore` and `git status` shows no DB or CSV files staged
- [ ] `.env` is not staged
- [ ] `ENVIRONMENT=production` is set in Render dashboard
- [ ] `SECRET_KEY` is set in Render dashboard (non-default, ≥ 32 hex chars)
- [ ] Session cookie `secure=True` patch is in `app/auth.py`

**After deploy:**
- [ ] Render shell: `ls /data` — all databases present
- [ ] `GET /` responds 200
- [ ] `GET /wealth` (unauthenticated) redirects to `/login` (307)
- [ ] `GET /library` (unauthenticated) redirects to `/login` (307)
- [ ] `GET /expenses` (unauthenticated) redirects to `/login` (307)
- [ ] `GET /health` (unauthenticated) redirects to `/login` (307)
- [ ] Login with a valid user succeeds
- [ ] Attempting `GET /data/finance.csv` returns 404 (FastAPI has no such route)
- [ ] Attempting `GET /data/wealth.db` returns 404

---

## Database Backups

Render persistent disks are not automatically backed up on the free/starter tier. Before every deploy that touches a migration:

1. Open the Render shell.
2. Run `cp /data/wealth.db /data/wealth.db.bak` (and the same for each affected DB).
3. After verifying the deploy, delete the `.bak` files.

For a more durable approach, add a pre-deploy script that copies the databases to a local machine via `scp` before every push. This is manual but appropriate for a personal site at this scale.

---

## Adding a User in Production

SSH into the Render shell and run:

```bash
python scripts/create_user.py --username <name> --role <admin|user>
```

This writes to the `users` table in the SQLite DB on the persistent disk. There is no other way to provision users — do not add a self-registration flow.

---

## What This Standard Does Not Cover

- CDN or edge caching — not needed at this scale.
- Horizontal scaling beyond one Render instance — the SQLite-on-disk model is single-instance by design. If multi-instance is ever needed, migrate to Postgres first.
- CI/CD pipelines — Render's auto-deploy on push to `main` is sufficient.
