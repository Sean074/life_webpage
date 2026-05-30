#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../data"
DB="$DATA_DIR/app.db"

mkdir -p "$DATA_DIR"

sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/001_library.sql"
sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/002_users.sql"
sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/003_gallery.sql"

# 004 uses ALTER TABLE ADD COLUMN, which has no IF NOT EXISTS in SQLite.
# Skip if the column already exists.
if ! sqlite3 "$DB" "PRAGMA table_info(gallery_images);" | grep -q "^[0-9]*|rotation|"; then
    sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/004_gallery_rotation.sql"
fi

sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/005_wealth.sql"
sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/006_health.sql"
sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/007_expenses.sql"

# 008 uses ALTER TABLE ADD COLUMN — guard for idempotency
if ! sqlite3 "$DB" "PRAGMA table_info(users);" | grep -q "totp_secret"; then
    sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/008_2fa.sql"
fi

# 009 uses ALTER TABLE ADD COLUMN — guard for idempotency
if ! sqlite3 "$DB" "PRAGMA table_info(users);" | grep -q "session_version"; then
    sqlite3 "$DB" < "$SCRIPT_DIR/../migrations/009_session_version.sql"
fi

echo "Database initialisation complete."
