# Life — Path to v1

Updated 2026-06-13. Closed items moved to `closed_todo.md`.

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
  - Link to the Projects showcase page (Phase 3)
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

- [ ] **Projects showcase page** (public)
  - `GET /projects` — server-rendered page highlighting personal software projects (sbeam, smodal, atmos, 2D flutter, etc.)
  - Per project: name, one-line blurb, tech tags, status (alpha/beta), and links — repo + a live-demo link where one exists (e.g. smodal on Streamlit Cloud)
  - Data source: **static** — a `content/projects/` Markdown-with-frontmatter set (mirrors the blog) or a single `projects.yaml` loaded by `app/services/projects.py`. **No GitHub API** — keeps to the no-third-party-scripts / no-external-API rule
  - Add to public nav alongside Blog, Gallery, Contact; link to it from `/contact`
  - Optional: one screenshot per project served from `data/images` (reuse the gallery serving path), staying within the spartan aesthetic
- [ ] **Test mobile on actual Samsung phone**
  - Verify hamburger toggle, Today page, table scroll, chart heights
  - Mobile review findings addressed: hamburger nav, chart heights 80→200px, table scroll containers, Account username display, Today page with totals and 7-day tracker
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

## Phase 5 — Secrets vault (secured)

**Goal:** A private page to store passwords and other sensitive notes, with a stronger security posture than the other restricted areas. Unlike Wealth/Health (plaintext SQLite behind a session cookie), vault contents MUST be encrypted at rest with a key that is not stored beside the data.

**Decision gate (decide before building):** build an encrypted vault (Option A below) **vs.** just use a dedicated password manager (Bitwarden / 1Password / KeePass). A hand-rolled vault is high-stakes to get right — only build if integration / learning / genuinely low-stakes secrets justify it.

### Prerequisites (security hardening — do first)

- [ ] **Stand up a pytest suite** — the crypto round-trip (encrypt → store → decrypt, wrong-passphrase rejection) must not ship untested. Pulls forward the Phase 2 test item.
- [ ] **Hard-fail on default `SECRET_KEY` in production** ([app/auth.py:17](app/auth.py:17))
  - Currently only warns; a vault must refuse to start with `dev-secret-change-me` when not in debug.
- [ ] **Fix CSRF cookie kwargs** (Phase 2.5) before adding more POST forms.

### Build (Option A — encrypted at rest)

- [ ] **Migration `012_vault.sql`** — `secrets` table storing only `label`, `username`, ciphertext, `nonce`, `salt`, `category`, `notes_ciphertext`, timestamps; plus a KDF salt + passphrase verifier. Never store plaintext.
- [ ] **Crypto module `app/services/vault.py`**
  - Derive the key from a **separate vault passphrase** (not the login password) via Argon2id (`argon2-cffi`) or scrypt
  - Encrypt with AES-GCM (`cryptography`) or Fernet
  - Add the chosen dependency to `requirements.in` (and re-lock)
- [ ] **Unlock + auto-lock flow**
  - `POST /admin/vault/unlock` derives the key into a **short, auto-locking** session window (much shorter than the 7-day app session)
  - Step-up auth: gate behind `require_admin` **plus** a fresh TOTP / password re-entry
- [ ] **CRUD routes + templates** — list / add / edit / delete secrets; clipboard-copy button (minimal inline JS, allowed); monochrome spartan UI per `docs/visual_style.md`
- [ ] **Exclude vault rows from `/admin/export`** (Phase 2) and from all logs
- [ ] **Document recovery** — losing the passphrase means unrecoverable data, by design. Warn explicitly in the UI.

**Caveat (accept consciously):** server-side decryption means plaintext transits server RAM and the passphrase reaches the server. True zero-knowledge would decrypt client-side (WebCrypto), which conflicts with the server-rendered / minimal-JS ethos. For a single-user personal app, server-side with a session-scoped key + encryption at rest is a defensible middle ground.

---

## Deliberately not doing (per CLAUDE.md)

- OAuth / social login
- Blog comment system
- Email subscription / mailing list (see Phase 3 RSS — chosen instead, 2026-05-28)
- Plaid / bank API integrations
- Analytics, tracking pixels, third-party scripts
- Hosting on the aviation-regs Mac Mini (incompatible threat models — see review, 2026-05-28; confirmed 2026-05-29)
- Like/love/meh reaction buttons (see 2026-05-28 — private hit counters chosen instead)
