# Life — Path to v1

Updated 2026-05-29 after the second design review. Closed items removed; new items added; critical-path items flagged.

---

## ⚠️ Critical — next session

These are blockers for a working deploy. The codebase is in a half-finished DB consolidation: schema lives in `app.db` but pieces of the application still read from the legacy per-domain files. Until these land, login fails, transactions land in orphan DBs, and `/healthz` 500s on a fresh container.

- [x] **⚠️ Repoint `app/auth.py` at `app.db`**
  - [app/auth.py:11](app/auth.py:11) — `DB_PATH = Path(__file__).parent.parent / "data" / "library.db"` is still the legacy path
  - Change to `... / "data" / "app.db"`
  - Without this, the entire auth layer reads users from a file that `init_db.sh` no longer populates
- [x] **⚠️ Repoint route-level DB paths**
  - [app/routes/auth_routes.py:16](app/routes/auth_routes.py:16) — `os.path.join(..., "library.db")` → `app.db`
  - `app/routes/admin.py` — same audit (referenced in Phase 2.5 hygiene)
  - Use `Path(__file__).parent.parent.parent / "data" / "app.db"` to match the model layer
- [x] **⚠️ Verify every `app/models/*.py` reads from `app.db`**
  - Phase 2.5 standardization implies models are consistent, but worth grepping: `grep -r "library.db\|gallery.db\|wealth.db\|health.db\|expenses.db" app/`
  - Anything that surfaces is a bug
- [x] **⚠️ Audit the per-domain `init_db()` calls in `main.py` startup**
  - [app/main.py:31-36](app/main.py:31-36) calls `expenses_model.init_db()`, `health_model.init_db()`, `gallery_init_db()`, `wealth_model.init_db()`
  - If any of those still create tables in their old per-domain file, every container restart resurrects empty legacy DBs alongside `app.db`
  - Either delete the calls (since `init_db.sh` now owns schema for `app.db`) or confirm each one is now a no-op against the consolidated DB
- [x] **⚠️ Run `scripts/migrate_to_app_db.py` against the real data once**
  - All rows copied clean (449 transactions, 9 wealth accounts, 39 health records, 12 gallery images, 22 library items). Legacy DBs renamed to `.bak`. Script deleted.
- [x] **⚠️ Local Docker dry-run end-to-end** (gate for all of the above)
  - `docker build` (uses updated `requirements.lock`)
  - `docker run` with mounted volume
  - Run `init_db.sh` inside the container
  - Create admin user, log in, write a post, upload an image, edit a wealth account
  - `docker restart` — verify data survived and no orphan `.db` files appeared
  - Until this passes, do not deploy
- [x] **⚠️ Chain `init_db.sh` before `uvicorn` in container `CMD`**
  - `/healthz` opens `data/app.db?mode=ro`; on a fresh container before init, the file doesn't exist and the probe returns 500
  - Dokploy will refuse to mark the container healthy and may restart-loop
  - Options: change Dockerfile `CMD` to `bash -c "bash scripts/init_db.sh && uvicorn ..."`, or split into a one-shot init container, or relax `/healthz` to distinguish "DB missing" (503) from "DB unreachable" (500)
- [ ] **⚠️ Verify `backup.sh` is actually scheduled**
  - The script is correct; nothing in the repo wires it to a schedule
  - On Dokploy: either a sidecar cron container, host cron on the VPS that `docker exec`s in, or a Dokploy scheduled task
  - Verify by waiting 24h and confirming a timestamped directory appears under `/var/lib/dokploy/volumes/life-data/backups/`
- [x] **⚠️ Verify 2FA login flow actually challenges for TOTP**
  - Traced `POST /login` → on `totp_enabled=1`, sets only a 5-min signed `pending_2fa` cookie and redirects to `/login/2fa`. The real `session` cookie is **only** issued after `pyotp.TOTP(secret).verify(code)` succeeds at [auth_routes.py:184](app/routes/auth_routes.py:184). Confirmed not theatre.
- [x] **⚠️ Add 2FA backup codes (lockout recovery)**
  - 8 codes per batch, format `xxxxx-xxxxx`, bcrypt-hashed, single-use. Generated on TOTP confirm; regeneratable from `/admin/account` (requires password).
  - Login path: `/login/2fa/recovery` — same rate-limit pocket as TOTP; consumes code on success.
  - New migration: `migrations/011_backup_codes.sql`. New template: `app/templates/login_recovery.html`.
- [x] **⚠️ Re-run local Docker dry-run after backup-codes change**
  - Passed 2026-05-30: built fresh image (after pinning `fastapi==0.128.8` + `starlette<1.0` in `requirements.in` to resolve the starlette 1.x `TemplateResponse` API break), enabled 2FA, confirmed 8 codes shown once, verified TOTP login, verified backup-code login, confirmed count decrements (8→7), regenerated codes and confirmed old codes rejected.
- [x] **Verify `.env` is not tracked by git**
  - Verified 2026-05-30: `git ls-files .env` returned empty. Safe.

---

## Phase 1 — Security & operability (remaining)

- [ ] **Production env in Dokploy**
  - Set `HTTPS_ONLY=true` in the Dokploy environment tab
  - Confirm `SECRET_KEY` is fresh, not copied from `.env`
- [ ] **Validate `session_version` in `get_current_user`**
  - Migration 009 added the column; the admin password-change route presumably bumps it
  - Verify the auth layer actually compares the cookie's session-version claim against the user row — otherwise a stolen cookie still survives a password rotation
- [ ] **Reconcile `requirements.txt`**
  - Lock + Dockerfile are now the source of truth; `requirements.txt` is a stale third copy
  - Either delete `requirements.txt` and update README's `pip install -r requirements.txt` line, or auto-generate it from the lock — pick one
- [ ] **Migrate `templates.TemplateResponse` calls to starlette ≥1.0 API**
  - Currently pinned to `starlette<1.0` in `requirements.in` because all 32 call sites use the deprecated signature `TemplateResponse("name.html", {"request": request, ...})`
  - New signature is `TemplateResponse(request, "name.html", {...})` (request as first positional, dropped from context)
  - Until done, cannot upgrade past fastapi 0.128.8 (Docker test 2026-05-30 confirmed: `TypeError: unhashable type: 'dict'` from Jinja2 cache lookup on every page)
- [ ] **Narrow CSV-import exception catch** ([app/routes/expenses.py:113](app/routes/expenses.py:113))
  - Currently catches bare `Exception` and reports "Import failed: check file format"
  - Narrow to the parser-level errors; let real bugs surface

---

## Phase 2 — Data correctness

- [ ] **Blog slug uniqueness**
  - Check before insert; reject on collision with 422 + error message
- [ ] **CSV-import calibration**
  - Real export from each bank you actually use
  - One unit test per parser using a redacted real CSV
- [ ] **Wealth projection regression test**
  - One scenario with known inputs and hand-computed expected outputs
  - These numbers inform real financial decisions — they need to be auditable
- [ ] **Rate-limit dict prune** ([app/routes/auth_routes.py:19](app/routes/auth_routes.py:19))
  - Periodic sweep to drop empty entries
- [ ] **Data export (admin)**
  - CSV + JSON download endpoints for Expenses, Wealth (accounts + history), and Health
  - Mount under `/admin/export/<area>.<format>`, behind `require_admin`
  - **Rationale:** data ownership — if you ever leave this app, walk out with everything
- [ ] **Server-side code syntax highlighting in blog posts**
  - Enable the `codehilite` extension in the existing `markdown` pipeline (`app/services/blog.py`)
  - Add a Pygments stylesheet to the static CSS bundle (`bw` or `friendly` inverted for the monochrome aesthetic)
  - Add `<span class="...">` and the highlight `<div>`/`<pre>` classes to the `bleach` allowlist in `services/blog.py` so highlighted output survives sanitization
- [ ] **Static `/contact` page**
  - `mailto:` link to a dedicated alias (e.g. `sean+site@gmail.com` or `contact@yourdomain.com`)
  - LinkedIn / GitHub / professional links on the same page
  - Add to public nav alongside Blog and Gallery
  - **No form** — avoids SMTP credentials, honeypot/rate-limit code, and another public POST endpoint

---

## Phase 2.5 — Code hygiene

**Goal:** Remove accumulated dead code and inconsistencies before the codebase grows further. None of these change behaviour — they make the next phase easier to navigate.

### Dead code removal

- [ ] **Remove unused imports**
  - `RedirectResponse` from `app/auth.py:9`
  - `timedelta` from `app/routes/expenses.py:1`
- [ ] **Remove `all_categories`**
  - Remove the import from `app/routes/gallery.py:14`
  - Delete the `all_categories()` function from `app/models/gallery.py`
- [ ] **Remove dead model functions**
  - `get_account()` from `app/models/wealth.py:41`
  - `delete_item()` from `app/models/library.py:107`
  - `generate_missing_thumbs()` from `app/services/gallery.py:144`
- [ ] **Remove or wire up `issue_csrf()`** (`app/auth.py:133`)
  - Defined but never called — all routes inline token generation
  - Either delete it or replace the ~30 inline occurrences with calls to it
  - Pairs with the "central CSRF dependency" intent from Phase 1

### Pattern consistency

- [ ] **Standardize model DB connections** to `with _connect() as conn:`
  - `app/models/expenses.py`, `app/models/wealth.py`, `app/models/health.py` use manual `try/finally conn.close()`
  - `app/auth.py` also uses the try/finally pattern
- [ ] **Add `PRAGMA foreign_keys = ON`** to `_connect()` in `expenses.py`, `wealth.py`, `health.py`
- [ ] **Standardize `DB_PATH`** (note: this is the cleanup; the urgent app.db repoint is in the Critical section above)
- [ ] **Fix CSRF cookie kwargs** in `app/routes/auth_routes.py` (6 occurrences)
  - Hardcodes `httponly=False, samesite="lax"` instead of `**_CSRF_COOKIE_KWARGS`
- [ ] **Move inline `import logging`** in `app/routes/expenses.py:108` to top of file

### Route thinning

- [ ] **Extract raw DB queries out of `auth_routes.py`** into `app/models/users.py` or `app/auth.py`
- [ ] **Extract raw DB queries out of `admin.py`** — password change, 2FA enable/disable belong in model functions

### Stale file cleanup

- [ ] **Archive or delete `docs/render_standard.md`**
  - References old per-DB files and Render deployment
- [ ] **Fix `deployment_for_dummy.md` line 155**
  - Still has the old `for f in migrations/*.sql; do sqlite3 data/expenses.db...` loop; replace with `bash scripts/init_db.sh`
- [x] **Delete `scripts/migrate_to_app_db.py`** once the Critical-section migration run is complete
- [ ] **Archive Hetzner legacy scripts**
  - `scripts/deploy.sh` and `scripts/server_setup.sh` — move to `docs/legacy/` or delete

---

## Phase 3 — Usability

**Goal:** The app is something you'd actually open daily.

- [ ] **Mobile pass on all restricted pages**
  - Narrow viewport, large tap targets
  - Table-to-card collapse where needed (Expenses transactions especially)
  - Test on the actual phone you'll use, not just Chrome DevTools
- [ ] **Smoke test script** (`scripts/smoke.sh`)
  - Hits each public route, performs a login, hits one restricted GET
  - Run after every deploy
- [ ] **Upload policy**
  - Document and enforce: max file size, max image dimensions, what happens when storage fills
  - Add a `df` check or storage-quota guard before accepting uploads
- [ ] **Gallery captions in lightbox**
  - Surface the existing `image.title` field as a single line of text below the lightbox `<img>` — short captions like "Oil on canvas: Master Copy Rembrandt" or "Glacier Peak Sunset"
  - Also add `title="{{ image.title }}"` to the thumbnail `<img>` for a free native hover tooltip on desktop
  - **Not** rendered under the thumbnail itself — keeps the grid visually restrained
  - Audit existing rows and backfill missing titles via the edit flow
- [ ] **Uptime monitoring**
  - UptimeRobot (or equivalent) hitting `/healthz` every 5 minutes
  - Email/push alert on failure
- [ ] **RSS feeds** (the site's only "follow" mechanism)
  - `GET /blog/feed.xml` — Atom or RSS 2.0, last 20 published posts, full content
  - `GET /gallery/feed.xml` — last 20 uploaded images, title + thumbnail URL in `<enclosure>` or `<media:content>`
  - `<link rel="alternate" type="application/rss+xml">` in `base.html` for auto-detect
  - Link to both from the `/contact` page
- [ ] **Year-in-review page** (admin only)
  - `/admin/review/<year>` — auto-generated summary across Health, Expenses, and Wealth
  - Default to the prior calendar year
  - Server-side rendered (no JS)
- [ ] **Private hit counters** (optional)
  - Server-side increment on `GET /blog/<slug>` and `GET /gallery` views
  - **Never displayed publicly** — viewable only on `/admin/stats` behind `require_admin`
  - Schema: single `views` table (`slug_or_image_id`, `kind`, `count`, `last_viewed`)

---

## Phase 4 — Once it's live

- [ ] **Restore drill**
  - Rebuild the VPS from scratch using only the Git repo + the latest backup
  - Time it. Document what was missing.
  - **Do this once before there's irreplaceable data on the live server.**
- [ ] **Retention policy**
  - Decide and document: keep all expense/wealth history forever, or trim after N years

---

## Deliberately not doing (per CLAUDE.md)

- OAuth / social login
- Blog comment system
- Email subscription / mailing list (see Phase 3 RSS — chosen instead, 2026-05-28)
- Plaid / bank API integrations
- Analytics, tracking pixels, third-party scripts
- Hosting on the aviation-regs Mac Mini (incompatible threat models — see review, 2026-05-28; confirmed 2026-05-29)
- Like/love/meh reaction buttons (see 2026-05-28 — private hit counters chosen instead)
