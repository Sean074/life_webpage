CREATE TABLE IF NOT EXISTS expense_categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO expense_categories (name) VALUES
    ('home'),
    ('entertainment'),
    ('shopping'),
    ('hobbies'),
    ('eating out'),
    ('other');

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    category    TEXT    NOT NULL DEFAULT 'other',
    account     TEXT    NOT NULL DEFAULT '',
    type        TEXT    NOT NULL DEFAULT 'debit'
);
