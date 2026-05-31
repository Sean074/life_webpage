# Web Deployment: A Plain-English Guide

This guide explains how a web application goes from code on your laptop to a live website anyone can visit. It uses this project (`seancomeara.tech`) as the concrete example throughout.

Originally written before the first deploy. Rewritten 2026-05-30 after the deploy actually happened, with all the gotchas baked in.

---

## The Big Picture

When you run the app locally (`uvicorn app.main:app --reload`), it only exists on your computer. To make it live on the internet you need three things:

1. **A server** — a computer that is always on and connected to the internet.
2. **A domain** — a human-readable address (e.g. `seancomeara.tech`) that points to that server.
3. **A way to package and run the app** so the server can host it reliably.

Everything else is layers around those three things. The rest of this doc explains the layers and the exact clicks/commands.

---

## The Layers, In Plain English

### Domain (the address)

A **domain name** (bought from a registrar like Hostinger, Namecheap, Cloudflare) is a label that maps to an IP address — the actual numerical address of your server (e.g. `177.7.32.219`).

Inside your domain's DNS settings you create an **A record**: "when someone types `seancomeara.tech`, send them to IP `177.7.32.219`". DNS changes can take a few minutes to a few hours to propagate globally.

Without a domain, users would have to type a raw IP address into their browser. DNS is the phone book that translates human names to machine addresses.

### VPS (the server)

A **VPS (Virtual Private Server)** is a rented slice of a physical machine in a data centre. It runs 24/7, has a public IP, and you control it completely via SSH. This project uses Hostinger.

```bash
ssh seanomeara@177.7.32.219
```

SSH gives you a terminal on the remote machine, as if you were sitting in front of it. We don't log in as `root` directly — we log in as a regular user and use `sudo` when we need superuser power.

**Why a VPS instead of your laptop?** Your laptop sleeps, changes IP addresses, sits behind a home router that blocks incoming connections. A VPS has a static public IP and never goes offline.

### Docker (packaging the app)

Your app works on your laptop because your laptop has the right version of Python, the right libraries, the right system tools. A fresh server has none of that. Setting it up manually is fragile, hard to repeat, and breaks the moment you forget what you did.

The `Dockerfile` in the project root is a **recipe**. It describes exactly how to build a **container image** — a self-contained bundle with the OS, Python, all dependencies, and your app code baked in.

```dockerfile
FROM python:3.11-slim          # start from an official Python image
RUN apt-get install ...        # install system libraries needed for image processing
COPY requirements.lock .       # copy the dependency list into the image
RUN pip install -r requirements.lock  # install Python packages
COPY app/ ./app/               # copy your actual application code
EXPOSE 8000
CMD ["bash", "-c", "bash scripts/init_db.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

The finished image is identical every time. It runs the same on your laptop, on the server, or anywhere else.

**Why `--host 0.0.0.0`?** By default uvicorn only listens on `localhost` (only accessible from inside the same machine). `0.0.0.0` means "accept connections from anywhere" — necessary for traffic from outside the container to reach it.

**Why `bash scripts/init_db.sh && uvicorn ...`?** The container starts with an empty `/app/data` directory (or whatever's in the bind-mounted volume). `init_db.sh` applies any missing SQL migrations to create/update tables before uvicorn boots. This prevents `/healthz` from 500ing on a fresh container.

### Traefik (the reverse proxy)

Your app inside the container listens on port `8000`. But browsers connect on port `80` (HTTP) and `443` (HTTPS). A **reverse proxy** sits in front of your app:

- Accepts connections on 80/443
- Looks at the domain name in each request
- Forwards the request to the right container on the right port
- Returns the response to the browser

**Traefik** is the reverse proxy this stack uses. It also handles **SSL termination** — it decrypts incoming HTTPS traffic and forwards plain HTTP to your app, so your app doesn't need to manage certificates at all. Traefik automatically requests free SSL certificates from **Let's Encrypt**.

If you ever run multiple apps on the same server, Traefik routes each domain to the correct container based on the hostname. One server, many sites, one proxy.

### Dokploy (the control panel)

**Dokploy** is a self-hosted PaaS (Platform as a Service) that gives you a web UI for everything above. It manages:

- Building Docker images from your Git repo
- Running and stopping containers
- Writing the routing config files that Traefik reads
- Triggering Let's Encrypt cert requests
- Showing you logs and a Terminal for each container

Think of it as a lightweight, self-hosted version of Heroku or Vercel. You install it once on the VPS, then everything else happens through `http://<vps-ip>:3000`.

---

## One-Time Server Setup

These steps only happen once per VPS. If you're deploying a NEW project to an existing Dokploy VPS, skip to the next section.

### S1 — Provision the VPS

1. Buy a VPS from Hostinger (Ubuntu 24.04 recommended; ~$5/mo plan is fine for a personal site).
2. Note the public IP address (e.g. `177.7.32.219`).
3. Wait for the email saying it's ready, then SSH in.

### S2 — Check for port conflicts (CRITICAL — we missed this the first time)

Many Hostinger VPS images come with **nginx pre-installed and running on port 80**. This will silently break Traefik later — Traefik can't bind to a port nginx is already holding.

Check and disable:

```bash
sudo ss -tulnp | grep -E ':(80|443) '
```

If you see `nginx` or anything other than `docker-proxy`/`traefik` listed, kill it before installing Dokploy:

```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
```

(If nothing's listed, you're good — skip to S3.)

### S3 — Install Dokploy

```bash
curl -sSL https://dokploy.com/install.sh | sudo sh
```

This takes ~2 minutes. It installs Docker (if missing), initialises Docker Swarm, creates the `dokploy-network`, deploys the Dokploy control plane on port 3000, and **deploys Traefik on ports 80/443**.

After it finishes, verify Traefik is actually running:

```bash
sudo docker ps --format '{{.Names}}' | grep traefik
```

You should see `dokploy-traefik`. If not (it happened to us), re-run the install script — it's idempotent and will create Traefik on the second pass.

Then verify the ports are claimed:

```bash
sudo ss -tulnp | grep -E ':(80|443) '
```

You should see both `:80` and `:443` with `docker-proxy` as the listening process.

### S4 — Create the Dokploy admin account

Open `http://<vps-ip>:3000` in your browser. First visit prompts you to create an admin account. Set a strong password and save it in your password manager.

### S5 — Register the VPS as a "server" inside Dokploy

This is non-obvious. Even though Dokploy is running ON the VPS, you have to tell Dokploy "this VPS is the server you should deploy apps to." Without this, the "Create Application" button is greyed out.

1. **Settings → Servers → + Add Server**.
2. Fill in:
   - **Name:** `local`
   - **IP Address:** the **PUBLIC** IP (`177.7.32.219`), NOT `127.0.0.1`. Using `127.0.0.1` will pass the SSH test but break DNS validation later because Dokploy compares your domain's public DNS answer against the IP stored here, and a private IP can never match.
   - **Port:** `22`
   - **Username:** `root`
   - **SSH Private Key:** click "Generate New Key" → Dokploy creates an ed25519 keypair → copy the **public** key it shows you → on the VPS, append it to `/root/.ssh/authorized_keys`:
     ```bash
     sudo mkdir -p /root/.ssh
     sudo chmod 700 /root/.ssh
     echo 'PASTE_THE_PUBLIC_KEY_HERE' | sudo tee -a /root/.ssh/authorized_keys
     sudo chmod 600 /root/.ssh/authorized_keys
     ```
3. Click **Test Connection** — should turn green.
4. **Save**.

### S6 — Connect Dokploy to GitHub (for private repos)

If your repo is **public**, skip this — Dokploy can clone via plain HTTPS without auth.

If **private**:

1. **Settings → Git → GitHub → Create GitHub App**.
2. Dokploy redirects you to GitHub with a pre-filled form. Give the app a unique name (e.g. `dokploy-yourname-life`) → submit.
3. GitHub redirects you back to Dokploy with the app credentials.
4. Click **Install** → choose your account → **Only select repositories** → tick the repo → **Install**.

---

## First Deploy (per project)

You're now ready to deploy a project. The numbered steps below correspond to what was actually done on `seancomeara.tech` on 2026-05-30. Times shown are rough — total walltime is ~30 min if nothing goes wrong, longer if it does.

### D1 — Create the project shell (~30 sec)

Dokploy → **Projects → Create Project** → name it `life` → Create.

### D2 — Create the application (~30 sec)

Inside the project → **+ Create Service → Application** → name `life-web` → Create.

You're now on the service detail page with tabs along the top (General, Environment, Logs, Domains, Advanced, etc.).

### D3 — Connect the Git source (~1 min)

**General tab:**

- **Provider:** GitHub (or Git, if using plain URL for a public repo)
- **Repository:** select from dropdown (or paste URL)
- **Branch:** `main`
- **Build Path:** `/`
- **Build Type:** Dockerfile
- **Dockerfile Path:** `./Dockerfile`
- **Save**.

### D4 — Environment variables (~2 min)

**Environment tab.** Add two variables:

```
SECRET_KEY=<long random hex string>
HTTPS_ONLY=true
```

Generate `SECRET_KEY` fresh for production — never reuse the value from your local `.env`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Why these matter:**
- `SECRET_KEY` signs session cookies and the `pending_2fa` cookie. If it leaks, an attacker can forge any user's login.
- `HTTPS_ONLY=true` makes the app set the `Secure` flag on cookies, so browsers refuse to send them over plain HTTP. Required when you have HTTPS in front (which Traefik gives you).

Save.

### D5 — Persistent volume (~2 min)

Containers are **ephemeral** — every new deploy throws away the old container and starts a fresh one. Without a persistent volume, your database and uploaded images would vanish on every deploy.

**On the VPS first**, create the host directory:

```bash
sudo mkdir -p /var/lib/dokploy/volumes/life-data/images
```

**In Dokploy:** Advanced tab → Volumes → **+ Add Mount** → type **Bind Mount**:

- **Host Path:** `/var/lib/dokploy/volumes/life-data`
- **Mount Path** (inside container): `/app/data`
- **Save**.

Now whenever the container reads/writes anything under `/app/data`, it actually happens at `/var/lib/dokploy/volumes/life-data` on the VPS's real disk. Survives container restarts and replacements.

### D6 — Domain + HTTPS (~5 min)

#### D6a — DNS at the registrar (Hostinger hPanel)

1. hPanel → Domains → `seancomeara.tech` → Manage → DNS/Nameservers → DNS Records.
2. **Check for an existing A record** for `@` (root domain). Hostinger usually pre-creates one pointing to their parking page.
   - If it exists: **edit** it (don't add a duplicate). Change "Points to" to the VPS IP. Set TTL to 300.
   - If not: **+ Add Record** → Type: A, Name: `@`, Points to: VPS IP, TTL: 300.
3. Also add the `www` variant: Type: CNAME, Name: `www`, Points to: `seancomeara.tech` (with trailing dot if required).
4. Save.
5. Wait ~2 min, then verify from your Mac:
   ```bash
   dig +short seancomeara.tech
   dig +short www.seancomeara.tech
   ```
   Both should return the VPS IP. If not, wait longer and retry.

**Do not proceed until `dig` returns the right IP.** If Dokploy tries to issue a Let's Encrypt cert before DNS propagates, the request fails and you go into a rate-limit penalty window.

#### D6b — Domain in Dokploy

`life-web` service → **Domains** tab → **+ Add Domain**:

- **Host:** `seancomeara.tech`
- **Path:** `/`
- **Container Port:** `8000` (matches `EXPOSE 8000` in the Dockerfile)
- **HTTPS:** ON
- **Certificate Provider:** Let's Encrypt
- **HTTP→HTTPS redirect:** ON
- **Save**.

Repeat for the `www` variant (`www.seancomeara.tech`).

Click **Validate DNS** on each — should turn green ✅. If red ("Domain resolves to X but should point to Y"), see the gotcha section below.

### D7 — Deploy (~2 min build + 30 sec)

Click **Deploy** (top-right of the service page). Watch the **Logs** tab.

Look for these landmark lines, in order:

```
Cloning into '/etc/dokploy/...'
...
Successfully built <hash>
Successfully tagged life-web:latest
Database initialisation complete.
INFO:     Started server process [1]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

"Database initialisation complete." means `init_db.sh` ran successfully — all migrations applied to a fresh `data/app.db`.

### D8 — Seed `data/` from local (~1 min)

The container is now running but `/app/data` only has the empty `app.db` that `init_db.sh` just created. It's missing `quotes.csv` (required by the home page), uploaded images, financial data files, etc.

Sync them from your local `data/` directory. Because your SSH user is non-root, do this in two steps:

**On your Mac:**

```bash
cd ~/Documents/Life
rsync -avz --progress \
  --exclude='.DS_Store' \
  --exclude='*.db.bak' \
  data/ seanomeara@<vps-ip>:/tmp/life-data-stage/
```

(Will ask for your VPS password.)

**On the VPS:**

```bash
sudo rsync -av /tmp/life-data-stage/ /var/lib/dokploy/volumes/life-data/
sudo chown -R root:root /var/lib/dokploy/volumes/life-data/
rm -rf /tmp/life-data-stage/
```

The bind mount is live — the container instantly sees the new files at `/app/data`. No restart needed.

If you don't want to seed `app.db` from local (e.g. start with a blank production DB), exclude it from the rsync and create a fresh admin via D9 instead.

### D9 — Create an admin user (only if you skipped seeding `app.db`)

If you synced your local `app.db` in D8, you already have your local admin user on production — skip this step.

If you started with a blank DB: `life-web` service → **Terminal** tab → opens a shell inside the running container.

```bash
python scripts/create_user.py --username sean --role admin
```

Set a strong password.

### D10 — First browser test

Visit `https://seancomeara.tech`. Expect: home page with 🔒 padlock in the address bar.

Log in. Go to `/admin/account` → enable 2FA if you haven't already. Save the 8 backup codes that appear (this is the only time they're shown).

---

## Common Gotchas (the things that broke our first deploy)

### "Internal Server Error" on every page after deploy

Symptom: `TypeError: unhashable type: 'dict'` in the container logs, in `jinja2/utils.py`.

Cause: dependency version drift. The project's `requirements.lock` (used by the Dockerfile) had a newer `starlette` (≥1.0) than the local `requirements.txt`. Starlette 1.0 changed the `TemplateResponse` signature — old: `TemplateResponse("name.html", {"request": request, ...})`; new: `TemplateResponse(request, "name.html", {...})`. The old code crashes on the new API.

Fix: pin `fastapi==0.128.8` and `starlette<1.0` in `requirements.in`, regenerate `requirements.lock`. Long-term fix: migrate all `TemplateResponse` call sites to the new API.

### "Internal Server Error" pointing to missing `data/quotes.csv`

Symptom: `FileNotFoundError: [Errno 2] No such file or directory: '/app/data/quotes.csv'`.

Cause: forgot D8 — the bind-mounted `data/` directory is empty.

Fix: run the rsync in D8.

### Browser shows "Connection timed out" / `ERR_CONNECTION_TIMED_OUT`

Cause: something is blocking ports 80/443 — either a leftover nginx on the host, a Hostinger panel-level firewall, or no Traefik installed at all.

Diagnose:

```bash
sudo ss -tulnp | grep -E ':(80|443) '
```

- Empty → nothing is listening; check if Traefik exists with `sudo docker ps | grep traefik`. If missing, re-run the Dokploy install script.
- Shows `nginx` → see S2.
- Shows `docker-proxy` for both 80 and 443 → ports are claimed by Traefik; the issue is elsewhere (probably the Hostinger control-panel firewall — check **VPS → Firewall** in hPanel and allow inbound 80/443).

### Browser shows "404 page not found" (from Traefik, not your app)

Cause: Traefik is running, the request is reaching it, but there's no routing rule for your domain. Dokploy writes per-service YAML files to `/etc/dokploy/traefik/dynamic/<service>.yml` whenever you add or edit a domain. If that file is missing, the domain → container mapping doesn't exist.

Diagnose:

```bash
ls -la /etc/dokploy/traefik/dynamic/
```

You should see a file for your service (e.g. `life-life-crtzvp.yml`). If missing, in the Dokploy UI: Domains tab → edit the domain → **Save** without changing anything. That forces Dokploy to re-write the YAML. If still missing, delete + re-add the domain.

### DNS Validation in Dokploy says "Domain resolves to X but should point to Y"

Cause: in S5 you registered the server with the wrong IP. If you used `127.0.0.1`, Dokploy compares your domain's public DNS answer (the real VPS IP) against `127.0.0.1` and they never match.

Fix: Settings → Servers → edit → change IP to the **public** VPS IP → Test Connection (should still pass thanks to NAT loopback) → Save. Then back in Domains, click Validate DNS again.

### "Authentication failed: Invalid SSH private key" after changing the server IP

Cause: SSH was working at `127.0.0.1` because it never actually opened an SSH connection. Now that the IP is the real public one, Dokploy is making real SSH and the key isn't in `/root/.ssh/authorized_keys`.

Fix: Settings → SSH Keys → generate a new key → copy public key → on the VPS, append to `/root/.ssh/authorized_keys` (see S5 step 2 commands). Back in the server settings, select that key, Test Connection.

### `git status` shows fewer changes than expected

Cause: someone (you, a previous Claude session) already committed the code on a different branch or in a previous session. The files on disk match HEAD because the changes were already in HEAD.

Fix: nothing to fix — that just means there's nothing to commit. Confirm with `git log --oneline -10`.

---

## Subsequent Deploys

After the first deploy, push commits to `main`:

```bash
git push origin main
```

Dokploy's webhook (configured during the GitHub App install) fires, rebuilds the image, swaps containers. Your data survives in the bind-mounted volume.

Or click **Deploy** in the Dokploy UI manually if you want to redeploy without a new commit (e.g. you changed an env var).

---

## Common Operations

| Task | How |
|------|-----|
| Deploy new code | `git push origin main` (auto) or click Deploy in UI |
| View logs | Dokploy → service → Logs tab (live tail) |
| Restart the app | Dokploy → service → Restart |
| Open a shell in the container | Dokploy → service → Terminal tab |
| Add a user | Terminal → `python scripts/create_user.py --username X --role user` |
| Apply new migrations | Migrations run automatically at container start (via `init_db.sh` in the Dockerfile CMD) |
| Back up `data/` | `rsync -avz seanomeara@<vps-ip>:/var/lib/dokploy/volumes/life-data/ ./data-backup/` |
| Inspect what Traefik thinks your routing is | `ls -la /etc/dokploy/traefik/dynamic/` then `cat <service>.yml` |
| See what's listening on ports 80/443 | `sudo ss -tulnp \| grep -E ':(80\|443) '` |
| Check Docker containers | `sudo docker ps` |
| Check Docker Swarm services | `sudo docker service ls` |

---

## Architecture: The Full Stack

```
Browser
  ↓ HTTPS (port 443)
Traefik (reverse proxy + Let's Encrypt SSL termination)
  ↓ HTTP (port 8000) over Docker overlay network
Docker container running uvicorn + FastAPI
  ↓ reads/writes
/app/data (bind-mounted from /var/lib/dokploy/volumes/life-data on the VPS)
  ↑ seeded from local via rsync (first deploy)
```

Each layer has one job:
- **Traefik** — receives traffic, routes by hostname, handles encryption
- **Docker** — packages and isolates the app from the host
- **Dokploy** — manages Docker builds + writes Traefik routing config through a UI
- **uvicorn** — Python process that runs FastAPI
- **FastAPI** — your application code
- **SQLite on a bind-mounted volume** — persistent data that survives deploys

---

## Pre-Deploy Sanity Checklist

Print this. Tick each before clicking Deploy on a NEW server.

- [ ] `sudo ss -tulnp | grep -E ':(80|443) '` shows ONLY `docker-proxy` (no nginx, apache, etc.)
- [ ] `sudo docker ps | grep traefik` returns a running `dokploy-traefik`
- [ ] Dokploy admin account created at `http://<vps-ip>:3000`
- [ ] Server registered in Dokploy with **public** IP (not 127.0.0.1)
- [ ] SSH Test Connection passes from Dokploy → server
- [ ] GitHub App connected (private repos only) OR repo is public
- [ ] `dig +short <domain>` returns the VPS IP
- [ ] `/var/lib/dokploy/volumes/<app>-data/` exists on the VPS
- [ ] `requirements.lock` was regenerated with `pip-compile` (if you edited `requirements.in`)
- [ ] Fresh `SECRET_KEY` generated for production (not reused from `.env`)
- [ ] `HTTPS_ONLY=true` set in production env vars
- [ ] Domain shows ✅ green Validate DNS in Dokploy
- [ ] You know what command to run to seed `data/` (rsync two-step)
