import csv
import random
from pathlib import Path

QUOTES_CSV = Path(__file__).resolve().parents[2] / "data" / "quotes.csv"

_quotes: list[dict] = []


def _load() -> None:
    """Read quotes.csv (columns quote,author,source). A missing file is the fresh-install case, not an error."""
    global _quotes
    if not QUOTES_CSV.exists():
        _quotes = []
        return
    with QUOTES_CSV.open(newline="", encoding="utf-8") as f:
        _quotes = list(csv.DictReader(f))


def random_quote() -> dict | None:
    """Return a random quote, or None when there are none (templates skip the footer)."""
    if not _quotes:
        _load()
    if not _quotes:
        return None
    return random.choice(_quotes)
