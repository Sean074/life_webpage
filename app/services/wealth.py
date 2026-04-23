from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path

FINANCE_CSV = Path(__file__).parent.parent.parent / "data" / "finance.csv"

_ACCOUNT_TYPES = {
    "acorn": "investment",
    "boa": "savings",
    "becu": "savings",
    "wise": "savings",
    "oz": "property",
    "etrade": "investment",
    "401k": "retirement",
    "super": "retirement",
    "debt": "liability",
}


def _parse_amount(val: str) -> float:
    val = val.strip().replace(",", "").replace("$", "").replace(" ", "")
    if not val:
        return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def _parse_date(raw: str) -> str | None:
    raw = raw.strip()
    # Try common formats
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%-m/%-d/%Y", "%-m/%-d/%y",
                "%d %B %Y", "%d %b %Y", "%d %B %y", "%d %b %y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # e.g. "3/17/22" — ambiguous two-digit year
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", raw)
    if m:
        mo, dy, yr = m.groups()
        year = 2000 + int(yr)
        return date(year, int(mo), int(dy)).isoformat()
    return None


def _account_type(name: str) -> str:
    key = name.lower().split("(")[0].strip()
    for k, v in _ACCOUNT_TYPES.items():
        if k in key:
            return v
    return "savings"


def load_history() -> list[dict]:
    """Return [{date, net_worth}] sorted by date from finance.csv."""
    with FINANCE_CSV.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        date_cols = header[1:]
        parsed_dates = [_parse_date(d) for d in date_cols]

        # Accumulate net worth per date index
        totals: dict[int, float] = {i: 0.0 for i in range(len(date_cols))}
        for row in reader:
            if not row or not row[0].strip():
                continue
            for i, val in enumerate(row[1:]):
                totals[i] += _parse_amount(val)

    result = []
    for i, d in enumerate(parsed_dates):
        if d:
            result.append({"date": d, "net_worth": round(totals[i], 2)})
    result.sort(key=lambda x: x["date"])
    return result


def latest_accounts_from_csv() -> list[dict]:
    """Return accounts seeded from the most recent CSV column."""
    with FINANCE_CSV.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        date_cols = header[1:]
        # Find rightmost non-empty date
        last_idx = len(date_cols) - 1
        while last_idx > 0 and not date_cols[last_idx].strip():
            last_idx -= 1
        last_date = _parse_date(date_cols[last_idx]) or date.today().isoformat()

        accounts = []
        for row in reader:
            if not row or not row[0].strip():
                continue
            name = row[0].strip()
            # Find the rightmost non-empty value for this account
            val = 0.0
            for idx in range(last_idx, -1, -1):
                raw = row[idx + 1] if idx + 1 < len(row) else ""
                if raw.strip():
                    val = _parse_amount(raw)
                    break
            accounts.append({
                "name": name,
                "balance": val,
                "type": _account_type(name),
                "institution": name,
                "last_updated": last_date,
            })
    return accounts


def current_net_worth(accounts: list[dict]) -> float:
    return round(sum(a["balance"] for a in accounts), 2)


def run_backward_projection(params: dict, start_net_worth: float) -> list[dict]:
    """Project backwards 5 years from current net worth using inverted model."""
    current_year = date.today().year
    salary = float(params["annual_salary"])
    spending = float(params["annual_spending"])
    salary_growth = float(params["salary_growth_rate"])
    inflation = float(params["inflation_rate"])
    inv_return = float(params["investment_return_rate"])

    rows = [{"year": current_year, "net_worth": round(start_net_worth, 0)}]
    nw = start_net_worth
    for k in range(1, 6):
        # nw_prev = (nw_current - income_at_prev + spending_at_prev) / (1 + r)
        income_k = salary / ((1 + salary_growth) ** k)
        spending_k = spending / ((1 + inflation) ** k)
        nw = (nw - income_k + spending_k) / (1 + inv_return)
        rows.append({"year": current_year - k, "net_worth": round(nw, 0)})

    rows.sort(key=lambda x: x["year"])
    return rows


def run_projection(params: dict, start_net_worth: float) -> list[dict]:
    current_year = date.today().year
    horizon = int(params["horizon_year"])
    retirement = int(params["retirement_year"])

    salary = float(params["annual_salary"])
    spending = float(params["annual_spending"])
    salary_growth = float(params["salary_growth_rate"])
    inflation = float(params["inflation_rate"])
    inv_return = float(params["investment_return_rate"])
    retirement_adj = float(params["retirement_spending_adj"])

    net_worth = start_net_worth
    rows = []
    for year in range(current_year, horizon + 1):
        income = salary if year < retirement else 0.0
        inv_growth = net_worth * inv_return
        net_worth = net_worth + income - spending + inv_growth
        rows.append({
            "year": year,
            "income": round(income, 0),
            "spending": round(spending, 0),
            "investment_growth": round(inv_growth, 0),
            "net_worth": round(net_worth, 0),
        })
        # Grow for next year
        salary *= (1 + salary_growth)
        if year >= retirement:
            spending *= (1 + inflation)
        else:
            spending *= (1 + inflation)
        if year == retirement - 1:
            spending *= retirement_adj

    return rows
