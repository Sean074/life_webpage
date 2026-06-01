# Closed Items

Completed tasks moved from `todo.md`. Ordered by phase then approximate completion date.

---

## Critical — DB consolidation & deploy readiness

- [x] **⚠️ Repoint `app/auth.py` at `app.db`**
  - `app/auth.py:12` — changed `DB_PATH` to `... / "data" / "app.db"`.

- [x] **⚠️ Repoint route-level DB paths**
  - `app/routes/auth_routes.py` and `app/routes/admin.py` — no `library.db` references remain. All route-level DB access now goes through model functions that use `app.db`.

- [x] **⚠️ Verify every `app/models/*.py` reads from `app.db`**
  - Grepped; zero legacy DB references (`library.db`, `gallery.db`, etc.) found in `app/`.

- [x] **⚠️ Audit the per-domain `init_db()` calls in `main.py` startup**
  - `app/main.py:31-33` still calls `expenses_model.init_db()`, `health_model.init_db()`, `wealth_model.init_db()`. Each function opens `app.db` (via the model's `_connect()` which points to `app.db`) and runs its migration SQL idempotently. No orphan legacy DBs are created.

- [x] **⚠️ Run `scripts/migrate_to_app_db.py` against the real data once**
  - All rows copied clean (449 transactions, 9 wealth accounts, 39 health records, 12 gallery images, 22 library items). Legacy DBs renamed to `.bak`. Script deleted.

- [x] **⚠️ Local Docker dry-run end-to-end**
  - Passed: fresh build, mounted volume, `init_db.sh`, admin user created, post written, image uploaded, wealth account edited, container restarted — data survived, no orphan `.db` files.

- [x] **⚠️ Chain `init_db.sh` before `uvicorn` in container `CMD`**
  - `Dockerfile:23` — `CMD ["bash", "-c", "bash scripts/init_db.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000"]`

- [x] **⚠️ Verify 2FA login flow actually challenges for TOTP**
  - Traced `POST /login` → on `totp_enabled=1`, sets only a 5-min signed `pending_2fa` cookie and redirects to `/login/2fa`. The real `session` cookie is only issued after `pyotp.TOTP(secret).verify(code)` succeeds at `auth_routes.py:184`. Confirmed not theatre.

- [x] **⚠️ Add 2FA backup codes (lockout recovery)**
  - 8 codes per batch, format `xxxxx-xxxxx`, bcrypt-hashed, single-use. Generated on TOTP confirm; regeneratable from `/admin/account` (requires password).
  - Login path: `/login/2fa/recovery` — same rate-limit pocket as TOTP; consumes code on success.
  - `migrations/011_backup_codes.sql` and `app/templates/login_recovery.html` added.

- [x] **⚠️ Re-run local Docker dry-run after backup-codes change**
  - Passed 2026-05-30: built fresh image (after pinning `fastapi==0.128.8` + `starlette<1.0` in `requirements.in` to resolve the starlette 1.x `TemplateResponse` API break), enabled 2FA, confirmed 8 codes shown once, verified TOTP login, verified backup-code login, confirmed count decrements (8→7), regenerated codes and confirmed old codes rejected.

- [x] **Verify `.env` is not tracked by git**
  - Verified 2026-05-30: `git ls-files .env` returned empty. Safe.

---

## Phase 1 — Security & operability

- [x] **Validate `session_version` in `get_current_user`**
  - Verified 2026-05-30: `auth.py:77` compares cookie version against DB row; `admin.py` password-change increments the column and re-issues the cookie. Working correctly.

- [x] **Reconcile `requirements.txt`**
  - Regenerated 2026-05-30 via `pip-compile requirements.in` (no hashes) targeting Python 3.11. Tracks `requirements.lock`: fastapi==0.136.3, starlette==1.2.1, uvicorn==0.48.0.

- [x] **Migrate `templates.TemplateResponse` calls to starlette ≥1.0 API**
  - Migrated all 32 call sites 2026-05-30: `TemplateResponse(request, "name.html", {...})`. Removed `starlette<1.0` and `fastapi==0.128.8` pins from `requirements.in`; regenerated lock and txt. Now on starlette 1.2.1 / fastapi 0.136.3.

- [x] **Narrow CSV-import exception catch** (`app/routes/expenses.py`)
  - Narrowed 2026-05-30 to `(ValueError, KeyError, csv.Error, UnicodeDecodeError)`. Moved inline `import logging` and `import csv` to top of file (also closes the Phase 2.5 hygiene item).

---

## Phase 2 — Data correctness

- [x] **Blog slug uniqueness**
  - `app/routes/blog.py:93` — checks for existing slug before insert; rejects collision with 422 + error message in the form. Completed in commit `dc40127`.

---

## Phase 2.5 — Code hygiene

- [x] **Move inline `import logging` in `app/routes/expenses.py` to top of file**
  - Done as part of the Phase 1 narrow-exception-catch item (2026-05-30). `expenses.py:1-2` now has `import csv` and `import logging` at the top.

- [x] **Fix `deployment_for_dummy.md` line 155**
  - Resolved 2026-05-30: full rewrite of `deployment_for_dummy.md`. New version reflects Dokploy + Traefik deployment; includes Common Gotchas section. Old stale `sqlite3 data/expenses.db` loop removed.

- [x] **Delete `scripts/migrate_to_app_db.py`**
  - Deleted after the Critical-section migration run completed.

- [x] **Remove unused imports**
  - Removed `RedirectResponse` from `app/auth.py` and `timedelta` from `app/routes/expenses.py`. Completed 2026-05-31.

- [x] **Archive Hetzner legacy scripts**
  - Deleted `scripts/deploy.sh` and `scripts/server_setup.sh` 2026-05-30.
