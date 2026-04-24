# Deployment Guide — Hetzner VPS

## Prerequisites

- A Hetzner account (hetzner.com)
- A domain name pointed at the server's IP (A record)
- Your GitHub repo is accessible (or you'll SCP files up)

---

## 1. Provision the Server

In the Hetzner console:

- **Image:** Ubuntu 24.04
- **Type:** CX22 (2 vCPU / 4 GB RAM) — overkill but cheap
- **Add your SSH public key** during setup

```bash
# Verify you can log in
ssh root@<server-ip>
```

---

## 2. Run the Server Setup Script

Copy `scripts/server_setup.sh` to the server and run it as root:

```bash
scp scripts/server_setup.sh root@<server-ip>:~/
ssh root@<server-ip> "bash ~/server_setup.sh"
```

This script installs Python, nginx, certbot, and creates the `app` system user.

---

## 3. Deploy the Application

From your local machine:

```bash
# First deploy
bash scripts/deploy.sh <server-ip>

# Subsequent deploys — same command
bash scripts/deploy.sh <server-ip>
```

What `deploy.sh` does:
1. Rsync the app code (excludes `.env`, `data/`, `.venv/`)
2. On the server: installs/updates Python deps, restarts the systemd service

---

## 4. Configure the Environment

SSH into the server and create the `.env` file:

```bash
ssh app@<server-ip>
nano /home/app/life/.env
```

Paste and fill in:

```
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
```

Then restart the service:

```bash
sudo systemctl restart life
```

---

## 5. Set Up HTTPS

```bash
ssh root@<server-ip>
certbot --nginx -d yourdomain.com
```

Certbot auto-renews via a systemd timer — no further action needed.

---

## 6. Initialise the Database and Create Your User

```bash
ssh app@<server-ip>
cd /home/app/life
source .venv/bin/activate

# Run any pending migrations
for f in migrations/*.sql; do sqlite3 data/expenses.db < "$f" 2>/dev/null; done

# Create your admin user
python scripts/create_user.py --username <name> --role admin
```

---

## 7. Upload Existing Data (first deploy only)

The `data/` directory is gitignored. Copy your local databases and images up:

```bash
rsync -avz --progress data/ app@<server-ip>:/home/app/life/data/
```

---

## Ongoing Operations

| Task | Command |
|------|---------|
| Deploy new code | `bash scripts/deploy.sh <server-ip>` |
| View app logs | `ssh root@<server-ip> journalctl -u life -f` |
| Restart app | `ssh root@<server-ip> systemctl restart life` |
| Add a user | `ssh app@<server-ip> "cd /home/app/life && source .venv/bin/activate && python scripts/create_user.py --username X --role user"` |
| Backup databases | `rsync -avz app@<server-ip>:/home/app/life/data/ ./data-backup/` |

---

## Nginx Config Location

`/etc/nginx/sites-available/life` — created by `server_setup.sh`, updated by certbot.

## Systemd Service Location

`/etc/systemd/system/life.service` — created by `server_setup.sh`.
