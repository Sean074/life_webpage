CREATE TABLE IF NOT EXISTS gallery_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL DEFAULT (date('now'))
);

CREATE INDEX IF NOT EXISTS idx_gallery_images_category ON gallery_images (category);
CREATE INDEX IF NOT EXISTS idx_gallery_images_uploaded ON gallery_images (uploaded_at);
