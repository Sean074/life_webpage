#!/usr/bin/env bash
# Run once as root on a fresh Ubuntu 24.04 VPS.
set -euo pipefail

APP_USER=app
APP_DIR=/home/$APP_USER/life
DOMAIN=${1:-""}  # optional: pass your domain as first arg

echo "==> Updating packages"
apt-get update -q && apt-get upgrade -y -q

echo "==> Installing dependencies"
apt-get install -y -q python3 python3-pip python3-venv nginx certbot python3-certbot-nginx ufw

echo "==> Creating app user"
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER

echo "==> Creating app directory"
mkdir -p $APP_DIR/data/images
chown -R $APP_USER:$APP_USER /home/$APP_USER

echo "==> Configuring firewall"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "==> Writing systemd service"
cat > /etc/systemd/system/life.service <<EOF
[Unit]
Description=Life personal site
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable life

echo "==> Writing nginx config"
cat > /etc/nginx/sites-available/life <<EOF
server {
    listen 80;
    server_name ${DOMAIN:-_};

    client_max_body_size 20M;

    location /static/ {
        alias $APP_DIR/app/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /art/ {
        alias $APP_DIR/data/images/;
        expires 7d;
        add_header Cache-Control "public";
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=()" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/life /etc/nginx/sites-enabled/life
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "==> Server setup complete."
echo ""
if [ -n "$DOMAIN" ]; then
    echo "Run this to enable HTTPS:"
    echo "  certbot --nginx -d $DOMAIN"
else
    echo "Run this to enable HTTPS (replace with your domain):"
    echo "  certbot --nginx -d yourdomain.com"
fi
echo ""
echo "Next: run deploy.sh from your local machine."
