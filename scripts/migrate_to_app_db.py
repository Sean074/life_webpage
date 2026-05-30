#!/usr/bin/env python3
"""
One-time migration: copies all data from the legacy per-domain DB files into
the consolidated app.db. Run with the app STOPPED.

Prerequisites:
  1. Run `bash scripts/init_db.sh` first so app.db schema already exists.
  2. The old DB files must exist at data/{library,gallery,wealth,health,expenses}.db.

On success, each old DB is renamed to <name>.db.bak (recoverable for one week,
then safe to delete).
"""

import sqlite3
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
APP_DB = DATA_DIR / "app.db"

SOURCES = [
    (DATA_DIR / "library.db",  ["users", "library_items", "tags", "library_item_tags"]),
    (DATA_DIR / "gallery.db",  ["gallery_images"]),
    (DATA_DIR / "wealth.db",   ["wealth_accounts", "wealth_projection_params"]),
    (DATA_DIR / "health.db",   ["health_records"]),
    (DATA_DIR / "expenses.db", ["expense_categories", "transactions"]),
]


def row_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def main() -> None:
    if not APP_DB.exists():
        print(f"ERROR: {APP_DB} does not exist. Run `bash scripts/init_db.sh` first.")
        sys.exit(1)

    dest = sqlite3.connect(APP_DB)
    dest.execute("PRAGMA journal_mode=WAL")

    errors = []

    for src_path, tables in SOURCES:
        if not src_path.exists():
            print(f"SKIP: {src_path.name} not found")
            continue

        src = sqlite3.connect(src_path)
        src.row_factory = sqlite3.Row

        for table in tables:
            try:
                src_count = row_count(src, table)
                dest_before = row_count(dest, table)

                rows = src.execute(f"SELECT * FROM {table}").fetchall()
                if rows:
                    cols = rows[0].keys()
                    placeholders = ", ".join("?" * len(cols))
                    col_list = ", ".join(cols)
                    dest.executemany(
                        f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})",
                        [tuple(r) for r in rows],
                    )
                    dest.commit()

                dest_after = row_count(dest, table)
                inserted = dest_after - dest_before
                print(f"  {src_path.name} → {table}: {src_count} rows in source, {inserted} inserted, {dest_after} total")

                if inserted < src_count:
                    skipped = src_count - inserted
                    print(f"    NOTE: {skipped} rows skipped (already present or PK conflict — expected if re-running)")

            except Exception as exc:
                errors.append(f"{src_path.name}.{table}: {exc}")
                print(f"  ERROR copying {table} from {src_path.name}: {exc}")

        src.close()

    dest.close()

    if errors:
        print(f"\nMigration completed with {len(errors)} error(s). Review above before renaming old DBs.")
        sys.exit(1)

    print("\nAll tables copied successfully. Renaming old DB files to .bak ...")
    for src_path, _ in SOURCES:
        if src_path.exists():
            bak = src_path.with_suffix(".db.bak")
            src_path.rename(bak)
            print(f"  {src_path.name} → {bak.name}")

    print("\nDone. Deploy the updated app (pointing at app.db) and verify data.")
    print("Delete *.db.bak files after one week of confirmed operation.")


if __name__ == "__main__":
    main()
