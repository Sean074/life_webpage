from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "app.db"
MIGRATION = Path(__file__).parent.parent.parent / "migrations" / "006_health.sql"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript(MIGRATION.read_text())
    conn.commit()
    conn.close()


def get_records() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM health_records ORDER BY date DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_weekly_averages() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT
                MIN(date)              AS week_start,
                AVG(meals_cooked)      AS avg_meals,
                AVG(exercise_hours)    AS avg_exercise,
                AVG(drinks)            AS avg_drinks,
                AVG(art_hours)         AS avg_art,
                AVG(read_hours)        AS avg_read,
                AVG(tv_hours)          AS avg_tv
            FROM health_records
            GROUP BY strftime('%Y-%W', date)
            ORDER BY week_start
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_summary(days: int = 7) -> dict:
    conn = _connect()
    try:
        row = conn.execute("""
            SELECT
                AVG(meals_cooked)   AS avg_meals,
                AVG(exercise_hours) AS avg_exercise,
                AVG(drinks)         AS avg_drinks,
                AVG(art_hours)      AS avg_art,
                AVG(read_hours)     AS avg_read,
                AVG(tv_hours)       AS avg_tv
            FROM health_records
            WHERE date >= date('now', ?)
        """, (f"-{days} days",)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def upsert_record(date: str, meals_cooked: int, exercise_hours: float,
                  drinks: int, art_hours: float, read_hours: float,
                  tv_hours: float = 0) -> int:
    conn = _connect()
    try:
        cur = conn.execute("""
            INSERT INTO health_records
                (date, meals_cooked, exercise_hours, drinks, art_hours, read_hours, tv_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                meals_cooked   = excluded.meals_cooked,
                exercise_hours = excluded.exercise_hours,
                drinks         = excluded.drinks,
                art_hours      = excluded.art_hours,
                read_hours     = excluded.read_hours,
                tv_hours       = excluded.tv_hours
        """, (date, meals_cooked, exercise_hours, drinks, art_hours, read_hours, tv_hours))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
