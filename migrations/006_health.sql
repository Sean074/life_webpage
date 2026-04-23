CREATE TABLE IF NOT EXISTS health_records (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT    NOT NULL UNIQUE DEFAULT (date('now')),
    meals_cooked   INTEGER NOT NULL DEFAULT 0,
    exercise_hours REAL    NOT NULL DEFAULT 0,
    drinks         INTEGER NOT NULL DEFAULT 0,
    art_hours      REAL    NOT NULL DEFAULT 0,
    read_hours     REAL    NOT NULL DEFAULT 0,
    tv_hours       REAL    NOT NULL DEFAULT 0
);
