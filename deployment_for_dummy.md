# Web Deployment: A Plain-English Guide

This guide explains how a web application goes from code on your laptop to a live website anyone can visit. It uses this project as the concrete example throughout.

---

## The Big Picture

When you run the app locally (`uvicorn app.main:app --reload`), it only exists on your computer. To make it live on the internet you need three things:

1. **A server** — a computer that is always on and connected to the internet.
2. **A domain** — a human-readable address (e.g. `seanomeara.com`) that points to that server.
3. **A process** — a way to start your app on that server and keep it running.

Everything else is details around those three things.

---

## Part 1: The Domain

### What it is
A domain name (bought from a registrar like Namecheap or Cloudflare) is just a label that maps to an IP address — the actual numerical address of your server (e.g. `65.108.20.14`).

### The A Record
Inside your domain's DNS settings you create an **A record**: a rule that says "when someone types `yourdomain.com`, send them to IP `65.108.20.14`".

DNS changes can take a few minutes to a few hours to propagate globally.

**Why this matters:** Without a domain, users would have to type a raw IP address into their browser. DNS is the phone book that translates human names to machine addresses.

---

## Part 2: The Server (VPS)

### What it is
A **VPS (Virtual Private Server)** is a rented slice of a physical machine in a data centre. It runs 24/7, has a public IP, and you control it completely via SSH. This project uses Hostinger.

### SSH access
```bash
ssh root@<server-ip>
```
SSH (Secure Shell) gives you a terminal on the remote machine, as if you were sitting in front of it. `root` is the superuser account with full administrative rights.

**Why a VPS instead of your laptop?** Your laptop goes to sleep, changes IP addresses, and sits behind a home router that blocks incoming connections. A VPS has a static public IP and never goes offline.

---

## Part 3: Docker (Packaging the App)

### The problem Docker solves
Your app works on your laptop because your laptop has the right version of Python, the right libraries, and the right system tools installed. A fresh server has none of that. Setting it up manually is fragile and hard to repeat.

### What a Dockerfile does
The `Dockerfile` in the project root is a recipe. It describes exactly how to build a **container image** — a self-contained bundle with the OS, Python, all dependencies, and your app code baked in.

```dockerfile
FROM python:3.11-slim          # start from an official Python image
RUN apt-get install ...        # install system libraries needed for image processing
COPY requirements.txt .        # copy the dependency list into the image
RUN pip install -r requirements.txt  # install Python packages
COPY app/ ./app/               # copy your actual application code
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# ↑ the command that starts the app when the container runs
```

The finished image is identical every time it is built. It runs the same on your laptop, on the server, or anywhere else.

**Why `--host 0.0.0.0`?** By default uvicorn only listens on `localhost` (only accessible from inside the same machine). `0.0.0.0` means "accept connections from anywhere" — necessary for the outside world to reach it.

---

## Part 4: Dokploy (The Platform Layer)

Dokploy is a self-hosted PaaS (Platform as a Service) that runs on your VPS and manages:
- Building Docker images from your Git repo
- Running containers
- Routing traffic to the right container (via Traefik, a reverse proxy)
- Issuing and renewing SSL certificates (via Let's Encrypt)
- Giving you a web UI to do all of the above without typing raw Docker commands

Think of it as a lightweight, self-hosted version of Heroku or Railway.

### Installing Dokploy
```bash
ssh root@<server-ip>
curl -sSL https://dokploy.com/install.sh | sh
```
This runs Dokploy's installer script. Dokploy itself runs as a Docker container and starts on port `3000`. You visit `http://<server-ip>:3000` to finish setup in a browser.

---

## Part 5: Walking Through the First Deploy

### Step 1 — Connect your Git repo

In the Dokploy UI you link your GitHub account and select this repository. From then on, Dokploy knows where to pull code from.

**Why:** The server needs to get your code somehow. Pulling from Git is the standard approach — it gives you a full history and makes every deploy traceable to a specific commit.

### Step 2 — Tell Dokploy how to build and run it

- **Build type: Dockerfile** — Dokploy sees the `Dockerfile` and uses it to build the image.
- **Port: 8000** — tells Dokploy which port inside the container the app listens on, so it can route traffic to it.

### Step 3 — Set environment variables

Sensitive values like `SECRET_KEY` cannot be committed to Git (they would be public). Instead, you set them as environment variables in Dokploy's UI. The running container picks them up at startup.

```
SECRET_KEY=<random hex string>
```

`SECRET_KEY` is used to sign session cookies — if it leaks, an attacker can forge login sessions.

**Why not hardcode it?** Anyone who can read the repo (now or in Git history forever) would have your secret. Environment variables keep secrets out of source control.

### Step 4 — Persistent storage (volumes)

Containers are **ephemeral** — every new deploy throws away the old container and starts a fresh one. That would delete your database and uploaded images on every deploy.

To prevent this, you mount a **volume**: a directory on the host server that is mapped into the container. The app reads and writes to `/app/data` inside the container, but the data physically lives at `/var/lib/dokploy/volumes/life-data` on the server and survives container restarts and replacements.

```
Host path:      /var/lib/dokploy/volumes/life-data
Container path: /app/data
```

Before the first deploy, create the directory:
```bash
ssh root@<server-ip> "mkdir -p /var/lib/dokploy/volumes/life-data/images"
```

### Step 5 — Domain and SSL

In Dokploy's Domains tab you add `yourdomain.com`. Dokploy tells its built-in reverse proxy (Traefik) to route traffic for that domain to your container.

**SSL (HTTPS):** Dokploy automatically requests a certificate from Let's Encrypt, a free certificate authority. This encrypts all traffic between the browser and your server. Without SSL, passwords and session cookies travel in plain text — anyone on the same network could read them.

### Step 6 — Click Deploy

Dokploy:
1. Pulls your latest code from Git
2. Runs `docker build` using the Dockerfile
3. Stops the old container
4. Starts a new container from the fresh image
5. Traefik routes incoming traffic to it

This is called a **rolling deploy** — there is a brief moment of downtime between old and new, but for a personal site that is acceptable.

### Step 7 — Initialise the database

The volume exists but is empty on first deploy. You need to create the database tables. Use Dokploy's Terminal tab (a shell inside the running container):

```bash
for f in migrations/*.sql; do sqlite3 data/expenses.db < "$f" 2>/dev/null; done
python scripts/create_user.py --username <name> --role admin
```

**Migrations** are plain SQL files that define the database schema. Running them in order creates all the tables. You only need to run missing migrations on subsequent deploys if the schema changes.

**Creating an admin user** is separate from migrations because it is data, not schema — it inserts a row into the users table with a hashed password.

### Step 8 — Upload existing data (first deploy only)

The `data/` directory is excluded from Git (`.gitignore`) because it contains personal financial data and uploaded images. Copy it from your local machine to the server:

```bash
rsync -avz --progress data/ root@<server-ip>:/var/lib/dokploy/volumes/life-data/
```

`rsync` copies only files that have changed, shows progress, and preserves directory structure. It is much faster than `scp` for large directories.

---

## Part 6: What Happens on Every Subsequent Deploy

After the first setup, deploying new code is one step:

1. Push your changes to the tracked Git branch (`main`).
2. Dokploy's webhook detects the push and triggers a new build automatically.

Or manually click **Deploy** in the UI. The same build-stop-start cycle runs. Your data is safe because it lives in the persistent volume, not inside the container.

---

## Part 7: The Reverse Proxy (Traefik)

Your app listens on port `8000`. But browsers connect on port `80` (HTTP) and `443` (HTTPS). A **reverse proxy** sits in front of your app and:

- Accepts connections on 80/443
- Matches the domain name in the request
- Forwards the request to the right container on the right port
- Returns the response to the browser

Traefik is the reverse proxy Dokploy installs. It also handles SSL termination — it decrypts the HTTPS traffic and forwards plain HTTP to your app, so your app does not need to manage certificates at all.

If you later run multiple apps on the same server, Traefik routes each domain to the correct container based on the hostname.

---

## Part 8: Common Operations

| Task | How |
|------|-----|
| Deploy new code | Push to `main` (auto), or click Deploy in UI |
| View logs | Dokploy UI → Logs tab |
| Restart the app | Dokploy UI → Restart |
| Open a shell in the container | Dokploy UI → Terminal tab |
| Add a user | Terminal → `python scripts/create_user.py --username X --role user` |
| Backup databases | `rsync -avz root@<server-ip>:/var/lib/dokploy/volumes/life-data/ ./data-backup/` |

---

## Summary: The Full Stack

```
Browser
  ↓ HTTPS (port 443)
Traefik (reverse proxy, SSL termination)
  ↓ HTTP (port 8000)
Docker container running uvicorn + FastAPI
  ↓ reads/writes
/app/data (mounted from /var/lib/dokploy/volumes/life-data on the VPS)
```

Every layer has one job:
- **Traefik** — receives traffic, routes it, handles encryption
- **Docker** — packages and isolates the app
- **Dokploy** — manages Docker builds and the Traefik config through a UI
- **uvicorn** — the Python process that actually runs FastAPI
- **FastAPI** — your application code
- **SQLite on a volume** — persistent data that survives deploys
