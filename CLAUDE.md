# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal website with six areas: Blog, Gallery, Library (restricted), Expenses (restricted), Wealth (restricted), Health (restricted).

## Stack

- **Backend:** FastAPI
- **Frontend:** Jinja2 + HTMX; Svelte only if reactivity becomes complex
- **Database:** SQLite (local dev); write Postgres-compatible queries
- **Auth:** `itsdangerous` signed cookies + bcrypt — see `docs/auth_standard.md`
- **Styling:** Plain CSS or Tailwind — no component libraries
- **Markdown:** `python-markdown` or `mistune`

## Running Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY
uvicorn app.main:app --reload
```

To add a user: `python scripts/create_user.py --username <name> --role <admin|user>`

## Deploying

Hosted on a Hetzner CX22 VPS (Ubuntu 24.04) behind nginx. App runs as the `app` system user via a systemd service. Full steps in `docs/deploy.md`.

**First deploy (one-time server setup):**
```bash
scp scripts/server_setup.sh root@<server-ip>:~/
ssh root@<server-ip> "bash ~/server_setup.sh yourdomain.com"
bash scripts/deploy.sh <server-ip>           # sync code and install deps
ssh app@<server-ip> "nano /home/app/life/.env"  # set SECRET_KEY
ssh root@<server-ip> "certbot --nginx -d yourdomain.com"
rsync -avz data/ app@<server-ip>:/home/app/life/data/  # seed DBs and images
ssh app@<server-ip> "cd /home/app/life && source .venv/bin/activate && python scripts/create_user.py --username <name> --role admin"
```

**Subsequent deploys:**
```bash
bash scripts/deploy.sh <server-ip>
```

**Common ops:**
- Logs: `ssh root@<server-ip> journalctl -u life -f`
- Restart: `ssh root@<server-ip> systemctl restart life`
- Backup data: `rsync -avz app@<server-ip>:/home/app/life/data/ ./data-backup/`

The `data/` directory (DBs, images) is never in git — sync it manually with rsync.

## Architecture

```
app/
  main.py             # FastAPI entry point; mounts all routers; calls load_dotenv()
  auth.py             # get_current_user, require_auth, require_admin, session helpers
  routes/             # Thin handlers only — logic in services/
    auth_routes.py    # GET/POST /login, GET /logout
    library.py, blog.py, gallery.py, expenses.py, wealth.py, health.py
  models/             # Raw SQL only (prefer raw for simple queries)
  templates/          # Jinja2 HTML
  static/             # CSS, JS, images
content/
  posts/              # Markdown files with YAML frontmatter
  art/                # Image assets
data/                 # SQLite DB and financial data files (never commit)
docs/
  visual_style.md     # Required UI standard
  auth_standard.md    # Required auth standard
migrations/           # Plain .sql files — no migration framework
scripts/
  create_user.py      # CLI to add users to the DB
  server_setup.sh     # One-time VPS provisioning (run as root)
  deploy.sh           # Rsync + restart — run from local machine on every deploy
```

## Required Standards

**Auth:** All routes involving authentication or access control MUST follow `docs/auth_standard.md` exactly. This covers which dependency to use (`require_auth` vs `require_admin` vs `get_current_user`), CSRF protection, session handling, template guards, and role logic. Do not invent alternative patterns.

**Visual style:** All webpages MUST follow `docs/visual_style.md`. This covers palette, typography, layout, navigation, and every UI component. Do not deviate from it.

## Key Conventions

- Routes must stay thin — business logic in service modules.
- Raw SQL preferred; use ORM only if schema grows complex.
- Migrations as plain `.sql` files in `migrations/`.
- Server-side rendering preferred over client-side data fetching.
- Always pass the real `user` dict (from `get_current_user` or a dependency) into template context — never hardcode `True` or `None`.

## Feature Rules

**Blog:** Posts are Markdown in `content/posts/` with frontmatter (`title`, `date`, `tags`, `draft`). `draft: true` posts never render publicly. `GET /blog` lists all published posts (title, date, tags), most recent first. The landing page (`/`) shows the 3 most recent published posts. `GET /blog/<slug>` renders Markdown at 65ch measure. Routes: `GET /blog`, `GET /blog/<slug>` (public). `POST /blog/new`, `POST /blog/<slug>/edit`, `POST /blog/<slug>/delete` (admin only).

**Gallery:** Images referenced by path in DB. Lazy-load; never ship full-resolution to browser. `GET /gallery` is public. Upload routes are admin only.

**Library/Expenses/Wealth/Health:** All restricted — any logged-in user (`require_auth`) can view; write operations require `require_admin`. `/library` must not appear in sitemaps or public nav. Charts: server-rendered SVG or bundled JS chart library; no CDN scripts.

**Expenses transactions schema:** `date`, `amount`, `description`, `category`, `account`, `type` (debit). Tracks spending only — income/credit rows are not stored. CSV bulk import with configurable per-bank parser. Categories are user-defined in DB. Default seed categories: home, entertainment, shopping, hobbies, eating out, other. Top-level metrics: 6-month rolling average spend/day, 30-day average spend/day, and monthly totals for current month + prior 2. Monthly totals chart defaults to combined total; a dropdown allows filtering to a single category.

**Wealth accounts schema:** `balance`, `type`, `institution`, `last_updated`. Net worth = assets − liabilities. The accounts table is hidden by default and expands on user action. Projection chart shows a 5-year backward projection with a dashed line style; the actual net worth line (grey) is overlaid, limited to 5 years prior from the current date.

**Gallery:** Grid shows 3–6 thumbnails. Lightbox (high-resolution image in an overlay) is approved for the gallery. Upload route is `/gallery/upload` (admin only). Rotation always regenerates the thumbnail.

**Health:** Charts are line graphs showing the average daily value calculated over a rolling week window.

## Security Constraints

- CSRF protection on all POST forms — use the double-submit cookie pattern (see `docs/auth_standard.md`).
- Rate-limit `POST /login` — already implemented; do not remove.
- Sanitize all user-supplied content before rendering.
- Never commit `.env`, DB files, or financial data — enforce via `.gitignore`.

## Do Not

- Add OAuth, social login, or external auth providers.
- Add a blog comment system.
- Integrate Plaid or any bank/financial API.
- Add analytics, tracking pixels, or third-party scripts.
- Over-engineer — this is a personal site, not a SaaS product.
