# Design Note: Retire the Library area in favour of Paperless-ngx

Status: Accepted, 26 Oct 2026
Scope: removes the Library area (`/library`) from the site. Blog, Gallery, Expenses, Wealth and Health are unaffected.

---

## Context

The Library area was meant to catalogue the engineering reference library: PDFs under `~/Documents/Library`, with a title, author, discipline, description, comment, 1–5 rating and free tags per item. It has three pages:

| Page | What it does |
|------|--------------|
| `/library/sync` | Scans `LIBRARY_ROOT` for PDFs not yet in `library_items` and creates a row for each. Title comes from the filename, discipline from the parent folder. |
| `/library/search` | Filters on discipline, tag and rating, and runs a `LIKE` match on title, author and description. |
| `/library/review` + `/library/items/{id}/edit` | Lists items missing author, description or rating so they can be filled in by hand. |

Storage is migration `001_library.sql`: `library_items`, `tags` and `library_item_tags`.

### Why it never worked in production

`app/models/library.py` hard-codes:

```python
LIBRARY_ROOT = Path("/Users/seanomeara/Documents/Library")
```

That path exists only on the MacBook Air. In the Dokploy container it does not exist, so Sync finds nothing and the deployed Library is always empty. The feature only ever worked when the app was run locally on the Air. Nothing was entered by hand that needs keeping.

### What changed

The reference library has moved to the Mac mini (`/Volumes/Data/Library`). It is now indexed by **Paperless-ngx**, which runs in Docker on the mini and is reachable only over Tailscale at `http://mac-mini:8010`. Paperless does everything the Library area set out to do, and more:

| Life Library | Paperless-ngx |
|--------------|---------------|
| Sync: discover new PDFs, title from filename, discipline from folder | Consume folder with `PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS`; OCR on ingest |
| Search: `LIKE` on title, author and description | Full-text search of every page, plus filters on tags, correspondent and custom fields |
| `discipline` and `tags` | Tags (topic folders become tags automatically) |
| `author` | Correspondent |
| `ref_number` | `Ref number` custom field |
| `description`, `rating` | `Description` (text) and `Rating` (integer) custom fields |
| `comment` | Document notes |
| Review page | `inbox` tag (auto-applied to new documents) and an "Inbox" saved view |
| `require_auth` / `require_admin` | Paperless users; network access limited to the Tailscale tailnet |

Description and Ref number are filled in automatically by **paperless-gpt**, which reads each document's OCR text and writes custom fields using the local Ollama model on the mini. Nothing leaves the machine.

---

## Decision

Remove the Library area from Life. Paperless-ngx on the Mac mini is the single catalogue for the reference library.

Two catalogues of the same files would drift, and the Life version cannot see the files from where it is deployed. Making it work would mean syncing PDFs to the VPS or exposing the mini to the internet. Neither is worth it for a single-user, private catalogue that Paperless already provides.

---

## Changes

### Code

- Delete `app/models/library.py`, `app/routes/library.py` and `app/templates/library/` (`index`, `search`, `sync`, `review`, `edit`).
- `app/main.py`: remove the `library_router` import and `app.include_router(library_router)`.
- `app/templates/base.html`: remove the Library nav link.

### Database

Add `migrations/012_drop_library.sql`:

```sql
DROP TABLE IF EXISTS library_item_tags;
DROP TABLE IF EXISTS library_items;
DROP TABLE IF EXISTS tags;
```

`tags` is used only by the Library area (checked 26 Oct 2026: no other model, route or migration references it), so it goes too. Leave `001_library.sql` in place, because migrations are an append-only history.

### Docs

- `README.md` and `CLAUDE.md`: describe five areas, not six. Remove `library.py` from the file trees.
- `docs/auth_standard.md`: remove `GET /library`, `POST /library/sync` and `POST /library/items/{id}/edit` from the route tables.
- `docs/visual_style.md`: remove Library from the restricted-links list and delete the Library page description.
- Add this note as `docs/library_paperless.md`.

---

## Consequences

- `/library` returns 404 after deploy. It was never in sitemaps or public nav, so no external links break.
- The reference library is reachable only from devices on the Tailscale tailnet. That is acceptable for a private, single-user tool.
- One fewer area to maintain. `/library/sync` was also the only route that read the local filesystem outside `data/`, so that exception disappears too.
- If a Library link on the site is wanted later, it can be a plain nav link to `http://mac-mini:8010` behind `require_auth`. It will only resolve on tailnet devices. No catalogue code needs to come back for that.

---

## Verification

1. `pytest` passes with no library tests or imports left.
2. `grep -rn -i library app/` returns nothing (apart from unrelated uses of the word).
3. A fresh database built from all migrations has no `library_items`, `library_item_tags` or `tags` tables.
4. After deploy: `/library` returns 404, the nav has five areas, and the other areas load normally when logged in.
