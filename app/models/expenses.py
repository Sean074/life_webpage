from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "expenses.db"
MIGRATION = Path(__file__).parent.parent.parent / "migrations" / "007_expenses.sql"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript(MIGRATION.read_text())
    conn.commit()
    conn.close()


def get_transactions() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY date DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_transaction(date: str, amount: float, description: str,
                    category: str, account: str, type_: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO transactions (date, amount, description, category, account, type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (date, amount, description, category, account, type_),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_transaction(id: int, date: str, amount: float, description: str,
                       category: str, account: str, type_: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE transactions SET date=?, amount=?, description=?, "
            "category=?, account=?, type=? WHERE id=?",
            (date, amount, description, category, account, type_, id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_transaction(id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM transactions WHERE id=?", (id,))
        conn.commit()
    finally:
        conn.close()


def get_categories() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM expense_categories ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_category(name: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (name,)
        )
        conn.commit()
    finally:
        conn.close()


def delete_category(id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM expense_categories WHERE id=?", (id,))
        conn.commit()
    finally:
        conn.close()


def get_monthly_totals() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT
                strftime('%Y-%m', date) AS month,
                SUM(amount)             AS total
            FROM transactions
            WHERE type = 'debit'
            GROUP BY month
            ORDER BY month
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_category_totals() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE type = 'debit'
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_monthly_by_category() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT
                strftime('%Y-%m', date) AS month,
                category,
                SUM(amount)             AS total
            FROM transactions
            WHERE type = 'debit'
            GROUP BY month, category
            ORDER BY month, category
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_summary() -> dict:
    conn = _connect()
    try:
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN date >= date('now', '-6 months') THEN amount ELSE 0 END) / 182.0 AS avg_daily_6mo,
                SUM(CASE WHEN date >= date('now', '-30 days')  THEN amount ELSE 0 END) / 30.0  AS avg_daily_30d,
                SUM(CASE WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now')              THEN amount ELSE 0 END) AS month_0,
                SUM(CASE WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now', '-1 month')  THEN amount ELSE 0 END) AS month_1,
                SUM(CASE WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now', '-2 months') THEN amount ELSE 0 END) AS month_2
            FROM transactions
            WHERE type = 'debit'
        """).fetchone()
        d = dict(row) if row else {}
        return {k: (v or 0.0) for k, v in d.items()}
    finally:
        conn.close()
