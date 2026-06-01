import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "app.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def get_all_images() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM gallery_images ORDER BY uploaded_at DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_images_by_category(category: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM gallery_images WHERE category = ? ORDER BY uploaded_at DESC, id DESC",
            (category,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_image(image_id: int) -> "dict | None":
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM gallery_images WHERE id = ?", (image_id,)
        ).fetchone()
        return dict(row) if row else None


def insert_image(category: str, filename: str, title: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO gallery_images (category, filename, title) VALUES (?, ?, ?)",
            (category, filename, title),
        )
        return cur.lastrowid


def delete_image(image_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM gallery_images WHERE id = ?", (image_id,))


def update_rotation(image_id: int, rotation: int):
    with _connect() as conn:
        conn.execute(
            "UPDATE gallery_images SET rotation = ? WHERE id = ?", (rotation, image_id)
        )
