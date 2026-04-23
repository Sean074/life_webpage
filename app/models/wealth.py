from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "wealth.db"
MIGRATION = Path(__file__).parent.parent.parent / "migrations" / "005_wealth.sql"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed_accounts: list[dict] | None = None):
    conn = _connect()
    conn.executescript(MIGRATION.read_text())
    conn.commit()
    if seed_accounts:
        count = conn.execute("SELECT COUNT(*) FROM wealth_accounts").fetchone()[0]
        if count == 0:
            for acct in seed_accounts:
                conn.execute(
                    "INSERT INTO wealth_accounts (name, balance, type, institution, last_updated) VALUES (?,?,?,?,?)",
                    (acct["name"], acct["balance"], acct["type"], acct.get("institution", ""), acct["last_updated"]),
                )
            conn.commit()
    conn.close()


def get_accounts() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM wealth_accounts ORDER BY balance DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_account(account_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM wealth_accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_account(name: str, balance: float, type_: str, institution: str, last_updated: str, account_id: int | None = None) -> int:
    conn = _connect()
    try:
        if account_id:
            conn.execute(
                "UPDATE wealth_accounts SET name=?, balance=?, type=?, institution=?, last_updated=? WHERE id=?",
                (name, balance, type_, institution, last_updated, account_id),
            )
            conn.commit()
            return account_id
        else:
            cur = conn.execute(
                "INSERT INTO wealth_accounts (name, balance, type, institution, last_updated) VALUES (?,?,?,?,?)",
                (name, balance, type_, institution, last_updated),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def delete_account(account_id: int):
    conn = _connect()
    try:
        conn.execute("DELETE FROM wealth_accounts WHERE id = ?", (account_id,))
        conn.commit()
    finally:
        conn.close()


def get_projection_params() -> dict:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM wealth_projection_params WHERE id = 1").fetchone()
        if row:
            return dict(row)
        defaults = {
            "id": 1, "annual_salary": 0, "annual_spending": 0,
            "salary_growth_rate": 0.03, "inflation_rate": 0.025,
            "investment_return_rate": 0.07, "retirement_year": 2045,
            "retirement_spending_adj": 0.8, "horizon_year": 2055,
        }
        conn.execute(
            "INSERT INTO wealth_projection_params VALUES (?,?,?,?,?,?,?,?,?)",
            tuple(defaults[k] for k in ["id","annual_salary","annual_spending","salary_growth_rate",
                                         "inflation_rate","investment_return_rate","retirement_year",
                                         "retirement_spending_adj","horizon_year"]),
        )
        conn.commit()
        return defaults
    finally:
        conn.close()


def update_projection_params(params: dict):
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO wealth_projection_params
               (id, annual_salary, annual_spending, salary_growth_rate, inflation_rate,
                investment_return_rate, retirement_year, retirement_spending_adj, horizon_year)
               VALUES (1,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 annual_salary=excluded.annual_salary,
                 annual_spending=excluded.annual_spending,
                 salary_growth_rate=excluded.salary_growth_rate,
                 inflation_rate=excluded.inflation_rate,
                 investment_return_rate=excluded.investment_return_rate,
                 retirement_year=excluded.retirement_year,
                 retirement_spending_adj=excluded.retirement_spending_adj,
                 horizon_year=excluded.horizon_year""",
            (params["annual_salary"], params["annual_spending"], params["salary_growth_rate"],
             params["inflation_rate"], params["investment_return_rate"], params["retirement_year"],
             params["retirement_spending_adj"], params["horizon_year"]),
        )
        conn.commit()
    finally:
        conn.close()
