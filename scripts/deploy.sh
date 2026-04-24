#!/usr/bin/env bash
# Deploy local code to the VPS.
# Usage: bash scripts/deploy.sh <server-ip-or-hostname>
set -euo pipefail

SERVER=${1:?"Usage: $0 <server-ip>"}
APP_USER=app
APP_DIR=/home/$APP_USER/life
REMOTE=$APP_USER@$SERVER

echo "==> Syncing code to $SERVER"
rsync -az --progress \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='data/' \
    --exclude='.env' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    . $REMOTE:$APP_DIR/

echo "==> Installing Python dependencies"
ssh $REMOTE "cd $APP_DIR && python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt"

echo "==> Restarting service"
ssh root@$SERVER "systemctl restart life"

echo "==> Checking service status"
ssh root@$SERVER "systemctl is-active life && echo 'Service is running.'"

echo ""
echo "==> Deploy complete."
