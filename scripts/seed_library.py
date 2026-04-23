"""
Walk /Users/seanomeara/Documents/Library/ and insert a stub row for each PDF
that doesn't already exist in the database (matched by file_path).

Run from the project root:
    python scripts/seed_library.py
"""

import sys
from pathlib import Path

LIBRARY_ROOT = Path("/Users/seanomeara/Documents/Library")
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.library import DB_PATH, create_item, get_all_items

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

existing_paths = {item["file_path"] for item in get_all_items()}

added = 0
for pdf in sorted(LIBRARY_ROOT.rglob("*.pdf")):
    rel = str(pdf.relative_to(LIBRARY_ROOT))
    if rel in existing_paths:
        continue
    discipline = pdf.parent.name if pdf.parent != LIBRARY_ROOT else None
    title = pdf.stem.replace("_", " ").replace("-", " ")
    create_item({"title": title, "discipline": discipline, "file_path": rel})
    print(f"  + {rel}")
    added += 1

print(f"\nSeeded {added} item(s). Total in DB: {len(get_all_items())}")
