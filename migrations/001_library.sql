CREATE TABLE IF NOT EXISTS library_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_number  TEXT UNIQUE,
    title       TEXT NOT NULL,
    author      TEXT,
    discipline  TEXT,
    description TEXT,
    comment     TEXT,
    rating      INTEGER CHECK (rating BETWEEN 1 AND 5),
    file_path   TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS library_item_tags (
    item_id INTEGER NOT NULL REFERENCES library_items (id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags (id) ON DELETE CASCADE,
    PRIMARY KEY (item_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_library_items_discipline ON library_items (discipline);
CREATE INDEX IF NOT EXISTS idx_library_items_rating     ON library_items (rating);
CREATE INDEX IF NOT EXISTS idx_tags_name                ON tags (name);
