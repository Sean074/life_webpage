# Life — Path to v1

Phased plan from the 2026-05-28 design review. Items are roughly ordered for value within each phase.

---

## Phase 0 — Unbreak deployment

**Goal:** A first deploy that actually works end-to-end. Do all of these before pointing a domain at the VPS.

- [x] **Fix `.env.example`**
  - Blank out `SECRET_KEY` (currently ships a real-looking placeholder)
  - Set `HTTPS_ONLY=false` for local dev (current `true` silently breaks local login on plain http)
  - Add a comment that production must override `HTTPS_ONLY=true` via Dokploy env tab
- [x] **Write `scripts/init_db.sh`**
  - Maps each migration to its correct DB file:
    - `001_library.sql`, `002_users.sql` → `library.db`
    - `003_gallery.sql`, `004_gallery_rotation.sql` → `gallery.db`
    - `005_wealth.sql` → `wealth.db`
    - `006_health.sql` → `health.db`
    - `007_expenses.sql` → `expenses.db`
  - Idempotent — safe to re-run
  - Replace the broken `for f in migrations/*.sql; do sqlite3 data/expenses.db ...` loop in `docs/deploy.md` Step 7 with a call to this script
  - Update README Section 4 to call this script instead of two hand-rolled `sqlite3` invocations
- [x] **Reconcile `CLAUDE.md` with reality**
  - Replace Hetzner CX22 / systemd / nginx as primary with Hostinger / Dokploy / Traefik
  - Keep Hetzner as the "legacy" section, matching `docs/deploy.md`
- [x] **Local Docker dry-run**
  - `docker build -t life .`
  - `docker run -p 8000:8000 -v $(pwd)/data:/app/data --env-file .env life`
  - Run `init_db.sh` inside the container
  - Create an admin user, log in, write a blog post, upload an image
  - `docker restart` the container and verify data survived
  - Only after this passes — provision the Hostinger VPS

---

## Phase 1 — Security & operability

**Goal:** Hardening required before exposing the app to the public internet.

- [x] **Central CSRF dependency**
  - Replace the 12+ copies of `secrets.compare_digest(csrf_token, cookie_csrf)` with a single `verify_csrf` dependency
  - Single point of token *issuance* on GET routes too (currently scattered, inconsistently cleared)
- [x] **Production env**
  - Set `HTTPS_ONLY=true` in the Dokploy environment tab (separate from `.env.example`)
  - Confirm `SECRET_KEY` is a fresh `python -c "import secrets; print(secrets.token_hex(32))"` value, not copied from anywhere
- [x] **2FA (TOTP) on admin login**
  - `pyotp` for code generation/verification; QR code via `qrcode` library (both server-side, no JS)
  - Enrollment flow: admin scans QR with Authenticator / 1Password / Bitwarden, confirms with a code, secret stored on the user row
  - Login flow: after password verifies, prompt for 6-digit code; lock account after N bad codes (reuse the existing rate-limit pattern)
  - Add a `2fa_secret` column to `users`; nullable so `role=user` accounts can stay password-only
  - **Rationale:** Expenses + Wealth hold real financial data — a leaked admin password should not be enough to read or alter the ledger
- [x] **Admin account page (`/admin/account`)**
  - Change-password form: current password + new password + confirm new password
  - Re-verify current password before accepting the change; never trust session alone for security-critical mutations
  - On success, invalidate other sessions (rotate `SECRET_KEY`-derived signing or bump a per-user session version) so a stolen cookie can't survive the rotation
  - Also surfaces 2FA enrollment / re-enrollment from the same page
  - **Rationale:** currently `scripts/create_user.py` is the only way to rotate a password — requires SSHing into the container, which is enough friction that rotations get delayed
- [ ] **`GET /healthz` endpoint**
  - Opens a DB connection, returns `{"ok": true}`
  - Wire into Dokploy / Traefik healthcheck so a hung container is detected
- [ ] **Pin dependencies**
  - Replace `Pillow>=11.0.0` with an exact version
  - Consider `pip-compile` to generate a full `requirements.lock`
  - Rebuild reproducibility is a prerequisite for blaming bugs on code vs. environment
- [ ] **Verify Markdown sanitization**
  - Confirm `bleach` is actually used in `app/services/blog.py` when rendering Markdown to HTML
  - If not, wire it in — otherwise XSS via post body
- [ ] **Verify gallery upload validation**
  - `app/services/gallery.py` `save_image` must check:
    - File extension allowlist
    - Magic-byte check (Pillow open as image)
    - Max file size and max image dimensions
  - Reject everything else with a 422
- [ ] **Strip EXIF on gallery upload**
  - In `save_image` (and the same path used by `rotate_image`), re-encode the image without EXIF metadata before writing to disk
  - Pillow one-liner: open → `Image.new(img.mode, img.size)` + `paste` (or `img.getdata()` round-trip) → save without `exif=` kwarg
  - Apply to thumbnail generation too
  - **Rationale:** phone photos carry GPS coordinates, camera serial, and timestamps — publishing a photo of a painting should not also publish your home address
- [ ] **Nightly backups**
  - Cron on the VPS: `sqlite3 <db> ".backup '<dest>'"` for each DB (online backup — safe while DB is being written)
  - Destination: `/var/lib/dokploy/volumes/life-data/backups/YYYY-MM-DD/`
  - 7-day rotation
  - Weekly off-server `rsync` to laptop
  - **Plain `cp` of a live SQLite file is not safe — do not use it**
- [ ] **Custom 404 / 500 templates**
  - Match the visual style standard
  - Stop leaking FastAPI's default JSON error responses
- [ ] **Fix `POST /blog/<slug>/delete`** ([app/routes/blog.py:174](app/routes/blog.py:174))
  - Currently silently no-ops on CSRF mismatch — should return 400
- [ ] **Move `init_db()` calls out of module import**
  - Currently called at import time in [routes/expenses.py:12](app/routes/expenses.py:12), [routes/health.py:11](app/routes/health.py:11), [routes/gallery.py:11](app/routes/gallery.py:11), [routes/wealth.py:12](app/routes/wealth.py:12)
  - Move to a single FastAPI `startup` event in `app/main.py`

---

## Phase 2 — Data correctness

**Goal:** Trust the numbers. Do before relying on Expenses/Wealth for real decisions.

- [ ] **Consolidate to a single `app.db`**
  - One schema, one backup, one migration target
  - Removes the cross-DB migration confusion that caused Phase 0's broken deploy command
  - Migration script: copy tables out of each old DB into the new one, verify row counts, swap
- [ ] **Blog slug uniqueness**
  - Check before insert; reject on collision with 422 + error message
  - Currently can silently overwrite an existing post
- [ ] **CSV-import calibration**
  - Real export from each bank you actually use
  - One unit test per parser using a redacted real CSV
  - Catches the inevitable "dates are in a different format this month" failure mode
- [ ] **Wealth projection regression test**
  - One scenario with known inputs and hand-computed expected outputs
  - These numbers inform real financial decisions — they need to be auditable
- [ ] **Rate-limit dict prune** ([app/routes/auth_routes.py:19](app/routes/auth_routes.py:19))
  - Periodic sweep to drop empty entries
  - Minor — not a blocker, but easy
- [ ] **Data export (admin)**
  - CSV + JSON download endpoints for Expenses, Wealth (accounts + history), and Health
  - Mount under `/admin/export/<area>.<format>`, behind `require_admin`
  - One handler per area; let the model layer return the rows, the route serializes
  - **Rationale:** data ownership — if you ever leave this app, walk out with everything. Also unblocks ad-hoc spreadsheet analysis.
- [ ] **Server-side code syntax highlighting in blog posts**
  - Enable the `codehilite` extension in the existing `markdown` pipeline (`app/services/blog.py`)
  - Add a Pygments stylesheet to the static CSS bundle (pick one that matches the monochrome aesthetic — `bw` or `friendly` inverted)
  - No client-side JS; rendering stays server-side
  - Sanity-check that `bleach` (once wired per Phase 1) allows the `<span class="...">` tags Pygments emits
- [ ] **Static `/contact` page**
  - `mailto:` link to a dedicated alias (e.g. `sean+site@gmail.com` or `contact@yourdomain.com`) — not your primary address, so it can be rotated if spam picks up
  - Optional: LinkedIn / GitHub / other professional links on the same page
  - Add to public nav alongside Blog and Gallery
  - **No form** — avoids SMTP credentials, honeypot/rate-limit code, and another public POST endpoint (see 2026-05-28 discussion)

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
  - Surface the existing `image.title` field ([app/routes/gallery.py:61](app/routes/gallery.py:61)) as a single line of text below the lightbox `<img>` — short captions like "Oil on canvas: Master Copy Rembrandt" or "Glacier Peak Sunset"
  - Also add `title="{{ image.title }}"` to the thumbnail `<img>` for a free native hover tooltip on desktop (mobile and screen readers ignore it gracefully)
  - **Not** rendered under the thumbnail itself — keeps the grid visually restrained and works identically on mobile
  - Audit existing rows and backfill missing titles via the edit flow
  - **Rationale:** lightbox-only is the simplest implementation that works on both desktop and touch (see 2026-05-28 discussion)
- [ ] **Uptime monitoring**
  - UptimeRobot (or equivalent) hitting `/healthz` every 5 minutes
  - Email/push alert on failure
- [ ] **RSS feeds** (the site's only "follow" mechanism)
  - `GET /blog/feed.xml` — Atom or RSS 2.0, last 20 published posts, full content (not just excerpts — there are no ads to gate behind clicks)
  - `GET /gallery/feed.xml` — last 20 uploaded images, with title as the entry title and the thumbnail URL in `<enclosure>` or `<media:content>`
  - Discoverable: `<link rel="alternate" type="application/rss+xml">` in `base.html` so reader apps auto-detect
  - Link to both from the `/contact` page so readers can find them
  - **Rationale (see 2026-05-28 discussion):** chosen instead of an email subscription system. RSS gives readers a way to follow with zero personal data collected, no SMTP infra, no sender reputation to manage, no unsubscribe/GDPR compliance burden, and the likely audience for this site already uses RSS readers.
- [ ] **Year-in-review page** (admin only)
  - `/admin/review/<year>` — auto-generated summary across Health and Expenses
  - Health: totals and weekly-average trends for each tracked metric (meals cooked, exercise hours, drinks, art hours, read hours, TV hours) over the year
  - Expenses: total spend, spend per month, top categories, biggest single-month deltas
  - Wealth: net worth start vs. end, contribution breakdown if derivable
  - Default to the prior calendar year; allow `/admin/review/<year>` for any year with data
  - Server-side rendered (no JS), reuses the same chart style as the live pages
  - **Rationale:** fits the reflective tone of the site; a once-a-year readout is more useful than constantly-visible streaks (which tend to distort the underlying behavior)
- [ ] **Private hit counters** (optional)
  - Server-side increment on `GET /blog/<slug>` and `GET /gallery` views
  - One counter per post / per image; bot-filter by user-agent allowlist (real browsers only)
  - **Never displayed publicly** — viewable only on `/admin/stats` behind `require_admin`
  - Rationale: gives you "did anyone read this" without a public state-modifying endpoint or social-media dynamics that pull your writing/art toward what gets clicks (see 2026-05-28 discussion — chosen over like/love/meh reactions)
  - Schema: single `views` table (`slug_or_image_id`, `kind`, `count`, `last_viewed`)

---

## Phase 4 — Once it's live

**Goal:** Operational confidence.

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
- Hosting on the aviation-regs Mac Mini (incompatible threat models — see review, 2026-05-28)
