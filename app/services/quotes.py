import csv
import random
from pathlib import Path

_quotes: list[dict] = []

def _load():
    global _quotes
    path = Path(__file__).parents[2] / "data" / "quotes.csv"
    with open(path, newline="", encoding="utf-8") as f:
        _quotes = list(csv.DictReader(f))

def random_quote() -> dict:
    if not _quotes:
        _load()
    return random.choice(_quotes)
