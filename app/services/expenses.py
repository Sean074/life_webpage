from __future__ import annotations

import csv
import io
from datetime import datetime

from app.models import expenses as expenses_model


def _normalise_date(raw: str) -> str:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw.strip()


def _parse_amount(raw: str) -> tuple[float, str]:
    """Return (abs_amount, 'debit'|'credit')."""
    cleaned = raw.strip().replace(",", "").replace("$", "")
    value = float(cleaned)
    type_ = "credit" if value > 0 else "debit"
    return abs(value), type_


def _parse_becu_checking(text: str) -> list[dict]:
    lines = text.splitlines()
    # Find the real header row (starts with "Date,")
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("Date,"):
            start = i
            break

    reader = csv.DictReader(lines[start:])
    rows = []
    for row in reader:
        raw_amount = row.get("Amount", "").strip()
        if not raw_amount:
            continue
        amount, type_ = _parse_amount(raw_amount)
        rows.append({
            "date": _normalise_date(row["Date"]),
            "amount": amount,
            "description": row.get("Description", "").strip(),
            "category": "other",
            "account": "becu_checking",
            "type": type_,
        })
    return rows


def _parse_becu_credit_card(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        raw_amount = row.get("Amount", "").strip()
        if not raw_amount:
            continue
        amount, type_ = _parse_amount(raw_amount)
        rows.append({
            "date": _normalise_date(row["Posted Date"]),
            "amount": amount,
            "description": row.get("Payee", "").strip(),
            "category": "other",
            "account": "becu_credit_card",
            "type": type_,
        })
    return rows


PARSERS: dict[str, callable] = {
    "becu_checking": _parse_becu_checking,
    "becu_credit_card": _parse_becu_credit_card,
}


def parse_csv(bank: str, file_bytes: bytes) -> list[dict]:
    parser = PARSERS.get(bank)
    if not parser:
        raise ValueError(f"Unknown bank: {bank}")
    text = file_bytes.decode("utf-8", errors="replace")
    return parser(text)


def bulk_import(transactions: list[dict]) -> int:
    count = 0
    for t in transactions:
        if t.get("type") != "debit":
            continue
        expenses_model.add_transaction(
            t["date"], t["amount"], t["description"],
            t["category"], t["account"], "debit",
        )
        count += 1
    return count
