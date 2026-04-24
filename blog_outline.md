# Personal Website Outline — Sean O'Meara

Personal site built with FastAPI + Jinja2 + HTMX. Monochrome, terminal-aesthetic design (IBM Plex Mono, max 720px content / 960px dashboard pages). Footer on every page shows a random quote from `data/quotes.csv`.

---

## Pages

### Landing Page — `/`
- Brief intro (name, one-line bio)
- Links to the main public sections: Blog, Gallery
- No hero image, no animation — plain text
- in the left margin include thumbnail of three images from the gallery.  these should change with page reload. These shall ONLY be on the landing page.

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
- Admin only: upload images (### Gallery — `/gallery/upload` (restricted — any logged-in admin))
    - Images can be uploaded through a page in the private section.
    - Images may need to be rotated from their default. Rotation regenerates the thumbnail automatically, so the displayed thumbnail always reflects the current rotation.
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
- tracks spending (debit) only. Income (credit) is not tracked.
- Transaction schema: `date`, `amount`, `description`, `category`, `account`, `type` (debit)
- top level metric SHALL:
  - show the average per day spending (based on 6 month running average)
  - add a average spending for th past 30 days.
  - show total spending per month for the current month and the last 2.
- Categories are user-defined in DB
  - "home" transaction relate to place to live, HOA, rent, wifi, furniture
  - "entertainment" transactions related to entertainment, Netflix, movies, 
  - "shopping" transactions related to cloths, toys
  - "hobbies" transactions related to hobbies, art, climbing (REI), running
  - "eating out" transactions related to eating out, restraunts, coffee
  - "other"
- Charts: bar/line, monochrome — spending by category and over time
- the monthly totals chart shall show the total as default and provide a drop down to enable the plot to show each category.
- CSV bulk import with per-bank parser
- Admin only: import CSV, edit/delete transactions, manage categories

---

### Wealth — `/wealth` (restricted — any logged-in user)
- Page MUST display the chart before the table.
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
  - project backwards by 5 years use the projection model use a "---" line style
  - add the Net Worth line to the projection plot. line should be "grey" (limit to 5 years prior from current date).
- Admin only: add/update accounts, adjust projection parameters
  - update the value in a given account, use a fom require all accounts to be updated
   - use prior value as default
   - date should default to current date
  - wealth plot will update with new data.

---

### Health — `/health` (restricted — any logged-in user)
- Summary metrics at top; detail records below
- Health categories to be tracked, daily record
  - Cook 1, 2, or 3 meals
  - Exercise, hours exercised
  - Drink,  number of standard
  - Art, hours
  - Read, hours
  - TV, hours
- Charts: line graphs (average daily calculated over a week) for tracked metrics over time
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
