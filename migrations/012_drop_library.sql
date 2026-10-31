-- Retire the Library area (docs/library_paperless.md, 26 Oct 2026).
-- The reference library is now catalogued by Paperless-ngx on the Mac mini.
-- `tags` was used only by the Library area.
DROP TABLE IF EXISTS library_item_tags;
DROP TABLE IF EXISTS library_items;
DROP TABLE IF EXISTS tags;
