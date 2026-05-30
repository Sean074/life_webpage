#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="/app/data"
BACKUP_DIR="$DATA_DIR/backups/$(date +%Y-%m-%d)"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

src="$DATA_DIR/app.db"
dest="$BACKUP_DIR/app.db"
if [ -f "$src" ]; then
    sqlite3 "$src" ".backup '$dest'"
    echo "$(date -Iseconds) backed up app.db"
else
    echo "$(date -Iseconds) WARNING: $src not found, skipping"
fi

# Prune backup directories older than RETENTION_DAYS
find "$DATA_DIR/backups" -maxdepth 1 -type d -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' \
    -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

echo "$(date -Iseconds) backup complete. Retained last $RETENTION_DAYS days."
