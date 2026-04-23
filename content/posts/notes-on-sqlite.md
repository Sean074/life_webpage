---
title: Notes on SQLite
date: 2026-02-20
tags: sqlite, databases, python
draft: false
---

SQLite is the most deployed database in the world by a factor that makes the comparison absurd. Every iPhone, every Android phone, every browser, every macOS install has several SQLite databases running. It's not a toy. It's the quietest piece of critical infrastructure you interact with every day.

## When to Use It

Use SQLite when:
- You have one writer (or can serialize writes)
- Your data fits on one machine
- You want operational simplicity

The "one writer" limitation is often overstated. WAL mode allows concurrent reads alongside a single writer, and for most personal projects and small-to-medium web apps, the bottleneck is never the database.

## Python Integration

The `sqlite3` module in the standard library is all you need for most things. Set `row_factory = sqlite3.Row` and your results behave like dictionaries. No ORM required.

```python
conn = sqlite3.connect("data/app.db")
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
print(row["username"])  # works like a dict
```

## Backup Strategy

Copy the file. That's it. `cp data/app.db data/app.db.backup`. SQLite's durability guarantees mean a file copy is a valid backup if done while no write is in progress, or with `VACUUM INTO` for a consistent snapshot.

## Migrating Later

If you do eventually outgrow SQLite, the migration to Postgres is straightforward if you've written standard SQL. Write standard SQL. Don't use SQLite-specific syntax like `REPLACE INTO` unless you need it specifically.
