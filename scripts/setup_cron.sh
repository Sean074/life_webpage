#!/usr/bin/env bash
# Run once on the VPS as root to install the nightly backup cron job.
# Idempotent — safe to re-run.
set -euo pipefail

CRON_LINE="0 2 * * * docker exec \$(docker ps -q -f name=life) bash /app/scripts/backup.sh >> /var/log/life-backup.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "life-backup"; then
    echo "Cron job already installed — nothing to do."
    exit 0
fi

(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "Cron job installed. Runs daily at 02:00 server time."
echo "Logs: /var/log/life-backup.log"
echo ""
echo "To verify manually before waiting 24h:"
echo "  docker exec \$(docker ps -q -f name=life) bash /app/scripts/backup.sh"
echo "  ls /var/lib/dokploy/volumes/life-data/backups/"
