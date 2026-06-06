# Life — Path to v1

Updated 2026-05-31. Closed items moved to `closed_todo.md`.

---

## Phase 2 — Data correctness

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


### Pattern consistency

- [ ] **Standardize model DB connections** to `with _connect() as conn:`
  - `app/models/expenses.py`, `app/models/wealth.py`, `app/models/health.py` use manual `try/finally conn.close()`
  - `app/auth.py` also uses the try/finally pattern
- [ ] **Add `PRAGMA foreign_keys = ON`** to `_connect()` in `expenses.py`, `wealth.py`, `health.py`
- [ ] **Standardize `DB_PATH`**
- [ ] **Fix CSRF cookie kwargs** in `app/routes/auth_routes.py` (6 occurrences)
  - Hardcodes `httponly=False, samesite="lax"` instead of `**_CSRF_COOKIE_KWARGS`

### Route thinning

- [ ] **Extract raw DB queries out of `auth_routes.py`** into `app/models/users.py` or `app/auth.py`
- [ ] **Extract raw DB queries out of `admin.py`** — password change, 2FA enable/disable belong in model functions

### Stale file cleanup

- [ ] **Archive or delete `docs/render_standard.md`**
  - References old per-DB files and Render deployment

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
