# Life

Personal website with six areas: Blog, Gallery, Library, Expenses, Wealth, and Health.

## Stack

- **Backend:** FastAPI
- **Frontend:** Jinja2 + HTMX
- **Database:** SQLite (local), Postgres-compatible queries
- **Auth:** itsdangerous signed cookies + bcrypt
- **Styling:** Plain CSS

## Local Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Set SECRET_KEY to a long random string:
# python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run migrations

```bash
sqlite3 data/library.db < migrations/001_library.sql
sqlite3 data/library.db < migrations/002_users.sql
```

### 5. Create an admin user

```bash
python scripts/create_user.py --username <name> --role admin
```

Additional users (read-only access to restricted pages):

```bash
python scripts/create_user.py --username <name> --role user
```

### 6. Run the development server

```bash
uvicorn app.main:app --reload
```

The app will be available at http://localhost:8000.

**If you get `[Errno 48] Address already in use`**, a previous server process is still running. Stop it and restart:

```bash
# Find and kill the process on port 8000
lsof -ti :8000 | xargs kill -9

# Then start the server again
uvicorn app.main:app --reload
```

## Roles

| Role | Access |
|------|--------|
| `admin` | All pages + create, edit, delete |
| `user` | Restricted pages (read-only) |
| *(unauthenticated)* | Blog, Gallery, home |

## Project Structure

```
app/
  main.py             # FastAPI entry point
  auth.py             # Session helpers, require_auth, require_admin
  routes/
    auth_routes.py    # /login, /logout
    library.py, blog.py, gallery.py, expenses.py, wealth.py, health.py
  models/             # Raw SQL
  templates/          # Jinja2 HTML
  static/             # CSS, JS, images
content/
  posts/              # Markdown blog posts
  art/                # Image assets
data/                 # SQLite DB and financial data (never committed)
migrations/           # Plain .sql files — apply in order
scripts/
  create_user.py      # Add users to the DB
docs/
  visual_style.md     # UI standard
  auth_standard.md    # Auth patterns and conventions
```

## Notes

- `data/` and `.env` are gitignored — never commit them.
- See `docs/auth_standard.md` for auth conventions all routes must follow.
- See `docs/visual_style.md` for UI conventions all templates must follow.
