# Personal Website Outline — Sean O'Meara

Personal site built with FastAPI + Jinja2 + HTMX. Monochrome, terminal-aesthetic design (IBM Plex Mono, max 720px content width). Footer on every page shows a random quote from `data/quotes.csv`.

---

## Pages

### Landing Page — `/`
- Brief intro (name, one-line bio)
- Links to the main public sections: Blog, Gallery
- No hero image, no animation — plain text
- in the left margin include thumbnail of three images from the gallery.  these should change with page reload.

---

### Blog — `/blog` (public)
- Lists all published posts (title, date, tags) — most recent first
- Shows last 3 posts on landing page
- Individual post: `GET /blog/<slug>` — Markdown rendered to HTML, 65ch measure
- Admin only: new post (`POST /blog/new`), edit (`POST /blog/<slug>/edit`), delete (`POST /blog/<slug>/delete`)
- Posts stored as Markdown files in `content/posts/` with YAML frontmatter (`title`, `date`, `tags`, `draft`)
- `draft: true` posts never render publicly

---

### Gallery — `/gallery` (public)
- Sample grid of thumbnails (between 3 to 6)
- Selection of the thumbnail creates a window with the high resolution image.
- Category filter: Drawings / Paintings / Photography
- Lazy-load thumbnails.
- Images referenced by path in DB; assets in `content/art/`
- Admin only: upload images (### Gallery — `/gallery_load` (restricted — any logged-in admin))
    - Images can be uploaded through a page in the private section.
    - Images may need to be rotated from their default. This should be done prior to creation of the thumbnail, so the thumbnail has the correct orientation.
    - Loading the image creates the thumbnail and updates the gallery db.

---

### Login — `/login`
- Simple username + password form
- Rate-limited POST
- Redirects to `/` on success
- `GET /logout` clears session

---

### Library — `/library` (restricted — any logged-in user)
- Plain list of documents: title, date, one-line description
- Not in public nav; not in sitemaps
- Admin only: add/remove documents

---

### Expenses — `/expenses` (restricted — any logged-in user)
- Summary totals at top; detailed transaction table below
- Transaction schema: `date`, `amount`, `description`, `category`, `account`, `type` (debit/credit)
- Categories are user-defined in DB
- Charts: bar/line, monochrome — spending by category and over time
- CSV bulk import with per-bank parser
- Admin only: import CSV, edit/delete transactions, manage categories

---

### Wealth — `/wealth` (restricted — any logged-in user)
- Page MUST display the cart before the table.
- The table shall be hidden unless the user selects to expand the table.
- Net worth = assets − liabilities, shown at top
- Account list: `balance`, `type`, `institution`, `last_updated`
- Line chart of net worth over time (historical actuals)
- **Projection model** — estimates future net wealth based on configurable assumptions:
  - Inflation rate
  - Salary growth rate; retirement year (salary drops to 0 or defined pension)
  - Spending growth rate; retirement spending adjustment
  - Annual investment return rate
  - Outputs per projected year: annual income, annual spending, annual investment growth, total net wealth
  - Displayed as a line chart to a user-defined horizon
- Admin only: add/update accounts, adjust projection parameters

---

### Health — `/health` (restricted — any logged-in user)
- Summary metrics at top; detail records below
- Charts: line graphs for tracked metrics over time
- Admin only: add new records

---

## Navigation

- Top bar: site name (left), nav links (right)
- Unauthenticated: Blog, Gallery
- Authenticated: Blog, Gallery, Library, Expenses, Wealth, Health + Logout
- Active link underlined; no other treatment

---

## Global Elements

- **Footer:** random quote from `data/quotes.csv` on every page reload
- **Auth:** `itsdangerous` signed cookies + bcrypt; CSRF double-submit cookie on all POST forms
- **Style:** monochrome palette, IBM Plex Mono, no animations, no external scripts
