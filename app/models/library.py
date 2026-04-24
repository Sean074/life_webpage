import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "library.db"


_ITEM_COLS = {"title", "author", "ref_number", "discipline", "description", "comment", "rating", "file_path"}


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _attach_tags(conn, items):
    if not items:
        return []
    ids = [r["id"] for r in items]
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT lit.item_id, t.name FROM library_item_tags lit "
        f"JOIN tags t ON t.id = lit.tag_id WHERE lit.item_id IN ({placeholders})",
        ids,
    ).fetchall()
    tag_map: dict[int, list[str]] = {i: [] for i in ids}
    for r in rows:
        tag_map[r["item_id"]].append(r["name"])
    return [dict(item) | {"tags": tag_map[item["id"]]} for item in items]


def _sync_tags(conn, item_id: int, tags: list[str]):
    conn.execute("DELETE FROM library_item_tags WHERE item_id = ?", (item_id,))
    for name in tags:
        name = name.strip().lower()
        if not name:
            continue
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO library_item_tags (item_id, tag_id) VALUES (?, ?)",
            (item_id, tag_id),
        )


def get_all_items(discipline=None, tag=None, rating=None, query=None):
    with _connect() as conn:
        sql = "SELECT DISTINCT i.* FROM library_items i"
        params: list = []
        if tag:
            sql += " JOIN library_item_tags lit ON lit.item_id = i.id JOIN tags t ON t.id = lit.tag_id"
        sql += " WHERE 1=1"
        if discipline:
            sql += " AND i.discipline = ?"
            params.append(discipline)
        if rating:
            sql += " AND i.rating = ?"
            params.append(rating)
        if tag:
            sql += " AND t.name = ?"
            params.append(tag.strip().lower())
        if query:
            sql += " AND (i.title LIKE ? OR i.author LIKE ? OR i.description LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like, like])
        sql += " ORDER BY i.discipline, i.title"
        items = conn.execute(sql, params).fetchall()
        return _attach_tags(conn, items)


def get_item(item_id: int):
    with _connect() as conn:
        item = conn.execute("SELECT * FROM library_items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            return None
        return _attach_tags(conn, [item])[0]


def create_item(data: dict) -> int:
    tags = data.pop("tags", [])
    data = {k: v for k, v in data.items() if k in _ITEM_COLS}
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    with _connect() as conn:
        cur = conn.execute(
            f"INSERT INTO library_items ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        item_id = cur.lastrowid
        _sync_tags(conn, item_id, tags)
        return item_id


def update_item(item_id: int, data: dict):
    tags = data.pop("tags", None)
    data = {k: v for k, v in data.items() if k in _ITEM_COLS}
    assignments = ", ".join(f"{k} = ?" for k in data)
    assignments += ", updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"
    values = list(data.values()) + [item_id]
    with _connect() as conn:
        conn.execute(f"UPDATE library_items SET {assignments} WHERE id = ?", values)
        if tags is not None:
            _sync_tags(conn, item_id, tags)


def delete_item(item_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM library_items WHERE id = ?", (item_id,))


def all_tags() -> list[str]:
    with _connect() as conn:
        return [r["name"] for r in conn.execute("SELECT name FROM tags ORDER BY name").fetchall()]


def all_disciplines() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT discipline FROM library_items WHERE discipline IS NOT NULL ORDER BY discipline"
        ).fetchall()
        return [r["discipline"] for r in rows]


LIBRARY_ROOT = Path("/Users/seanomeara/Documents/Library")


def get_untracked_files() -> list[str]:
    with _connect() as conn:
        tracked = {
            r["file_path"]
            for r in conn.execute("SELECT file_path FROM library_items WHERE file_path IS NOT NULL").fetchall()
        }
    return sorted(
        str(p.relative_to(LIBRARY_ROOT))
        for p in LIBRARY_ROOT.rglob("*.pdf")
        if str(p.relative_to(LIBRARY_ROOT)) not in tracked
    )


def get_incomplete_items() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM library_items "
            "WHERE author IS NULL OR author = '' "
            "   OR rating IS NULL "
            "   OR description IS NULL OR description = '' "
            "ORDER BY discipline, title"
        ).fetchall()
        return _attach_tags(conn, rows)
