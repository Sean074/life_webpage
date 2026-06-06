# Deployment Guide

## Deployment Options

- **[Dokploy on Hostinger](#dokploy-on-hostinger-ubuntu-2404)** ← current/primary
- [Hetzner VPS (legacy systemd)](#hetzner-vps-legacy)

---

## Dokploy on Hostinger (Ubuntu 24.04)

Dokploy is a self-hosted PaaS that manages Docker containers, reverse proxying (Traefik), and SSL automatically. The app runs from the `Dockerfile` at the repo root.

### Prerequisites

- Hostinger VPS running Ubuntu 24.04 with root SSH access
- A domain with an A record pointed at the VPS IP
- Git repository accessible (GitHub, GitLab, etc.)

---

### 1. Install Dokploy on the VPS

```bash
ssh root@<server-ip>
curl -sSL https://dokploy.com/install.sh | sh
```

Dokploy will start on port `3000`. Visit `http://<server-ip>:3000` to complete the web UI setup and create your admin account.

---

### 2. Create the Application in Dokploy

In the Dokploy UI:

1. **Projects → New Project** → create a project (e.g. `life`)
2. **Add Service → Application**
3. **Source:** connect your Git provider and select this repo
4. **Build type:** Dockerfile (auto-detected from repo root)
5. **Port:** `8000`

---

### 3. Set Environment Variables

In the application's **Environment** tab, add:

```
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
```

---

### 4. Configure Persistent Storage

The `data/` directory holds the SQLite databases and uploaded images. It must persist across deploys.

In the application's **Mounts** tab, add a volume mount:

| Host path | Container path |
|-----------|---------------|
| `/var/lib/dokploy/volumes/life-data` | `/app/data` |

Create the directory on the VPS before first deploy:

```bash
ssh root@<server-ip> "mkdir -p /var/lib/dokploy/volumes/life-data/images"
```

---

### 5. Configure Domain and SSL

In the application's **Domains** tab:

1. Add your domain (e.g. `yourdomain.com`)
2. Enable **HTTPS** — Dokploy provisions Let's Encrypt automatically via Traefik

---

### 6. Deploy

Click **Deploy** in the Dokploy UI (or push to your configured branch — Dokploy can auto-deploy on push via webhook).

---

### 7. Initialise the Database and Create Your Admin User

After the first successful deploy, open the application's **Terminal** tab in Dokploy and run:

```bash
# Run migrations
bash scripts/init_db.sh

# Create admin user
python scripts/create_user.py --username <name> --role admin
```

---

### 8. Upload Existing Data (first deploy only)

The `data/` directory is gitignored. Copy your local databases and images to the persistent volume on the VPS:

```bash
rsync -avz --progress data/ root@<server-ip>:/var/lib/dokploy/volumes/life-data/
```

---

### 9. Schedule the Nightly Backup

SSH into the VPS as root and run the setup script:

```bash
ssh root@<server-ip>
bash /path/to/repo/scripts/setup_cron.sh
```

Or copy-paste the one-liner directly:

```bash
(crontab -l 2>/dev/null; echo "0 2 * * * docker exec \$(docker ps -q -f name=life) bash /app/scripts/backup.sh >> /var/log/life-backup.log 2>&1") | crontab -
```

Verify it was installed: `crontab -l`

Then do a manual dry-run to confirm the script works before waiting 24 hours:

```bash
docker exec $(docker ps -q -f name=life) bash /app/scripts/backup.sh
ls /var/lib/dokploy/volumes/life-data/backups/
```

A dated directory should appear. After 24 hours a second directory confirms the cron is running.

---

### Ongoing Operations

| Task | How |
|------|-----|
| Deploy new code | Push to the tracked branch (auto-deploy), or click **Deploy** in UI |
| View logs | Dokploy UI → application → **Logs** tab |
| Restart app | Dokploy UI → application → **Restart** |
| Add a user | Dokploy UI → application → **Terminal** → `python scripts/create_user.py --username X --role user` |
| Manual backup | `docker exec $(docker ps -q -f name=life) bash /app/scripts/backup.sh` |

---

### Backups

Nightly backups run via `scripts/backup.sh`, which uses the SQLite online backup API (`sqlite3 .backup`) — safe while the database is being written. **Never use plain `cp` on a live SQLite file.**

Each backup is written to a dated directory inside the data volume:
```
/var/lib/dokploy/volumes/life-data/backups/YYYY-MM-DD/
  app.db
```

Backups older than 7 days are pruned automatically.

#### Setting up the nightly cron on the VPS

SSH into the VPS as root and open the crontab:

```bash
ssh root@<server-ip>
crontab -e
```

Add this line:

```
0 2 * * * docker exec $(docker ps -q -f name=life) bash /app/scripts/backup.sh >> /var/log/life-backup.log 2>&1
```

This runs at 02:00 nightly. `docker ps -q -f name=life` resolves the current container ID by name — it survives redeployments. Logs accumulate at `/var/log/life-backup.log` on the host.

#### Weekly off-server rsync to laptop

Add to your laptop's crontab (`crontab -e` on macOS):

```
0 9 * * 0  rsync -avz --delete root@<server-ip>:/var/lib/dokploy/volumes/life-data/backups/ ~/backups/life/ >> ~/Library/Logs/life-backup-rsync.log 2>&1
```

This runs every Sunday at 09:00 and mirrors only the `backups/` subdirectory (not the live database files).

#### Restoring from a backup

1. Identify the backup date to restore from: `ls /var/lib/dokploy/volumes/life-data/backups/`
2. Copy the desired file into `/app/data/` inside the container:
   ```bash
   docker exec <container-id> cp /app/data/backups/YYYY-MM-DD/app.db /app/data/app.db
   ```
3. Restart the container: Dokploy UI → application → **Restart**

---

### Local Docker Testing

Before pushing, verify the container works locally:

```bash
docker build -t life .
docker run -p 8000:8000 -v $(pwd)/data:/app/data --env-file .env life
```

Visit `http://localhost:8000`.

---

## Hetzner VPS (legacy)

Traditional deploy: rsync + systemd + nginx + certbot. No Docker required.

### Prerequisites

- Hetzner account, CX22 server (Ubuntu 24.04), SSH key added
- Domain A record pointed at server IP

### 1. Provision and set up the server

```bash
scp scripts/server_setup.sh root@<server-ip>:~/
ssh root@<server-ip> "bash ~/server_setup.sh"
```

### 2. Deploy and configure

```bash
bash scripts/deploy.sh <server-ip>

ssh app@<server-ip>
nano /home/app/life/.env   # set SECRET_KEY
sudo systemctl restart life
```

### 3. HTTPS

```bash
ssh root@<server-ip>
certbot --nginx -d yourdomain.com
```

### 4. Database init and user creation

```bash
ssh app@<server-ip>
cd /home/app/life && source .venv/bin/activate
bash scripts/init_db.sh
python scripts/create_user.py --username <name> --role admin
```

### 5. Upload data

```bash
rsync -avz --progress data/ app@<server-ip>:/home/app/life/data/
```

### Ongoing Operations

| Task | Command |
|------|---------|
| Deploy new code | `bash scripts/deploy.sh <server-ip>` |
| View logs | `ssh root@<server-ip> journalctl -u life -f` |
| Restart app | `ssh root@<server-ip> systemctl restart life` |
| Add a user | `ssh app@<server-ip> "cd /home/app/life && source .venv/bin/activate && python scripts/create_user.py --username X --role user"` |
| Backup databases | `rsync -avz app@<server-ip>:/home/app/life/data/ ./data-backup/` |

Config file locations: nginx at `/etc/nginx/sites-available/life`, systemd at `/etc/systemd/system/life.service`.
