# Deploying Orator to a Hostinger VPS (Ubuntu)

This guide deploys the FastAPI backend (gunicorn + uvicorn) and Next.js frontend
(PM2) behind Nginx on a single Ubuntu VPS, with Let's Encrypt SSL via Certbot.

**Architecture:**
```
Internet → Nginx (80/443)
             ├── /api/*  → gunicorn:8000 (FastAPI, systemd)
             └── /       → next start:3000 (PM2)
```

---

## Prerequisites

- A Hostinger VPS running Ubuntu 22.04 (or 24.04).
- A domain name with an A record pointing to the VPS IP.
- SSH access to the VPS as root (or a sudo user).
- This repo pushed to GitHub.

---

## 1 — Connect and update the VPS

```bash
ssh root@YOUR_VPS_IP
apt update && apt upgrade -y
```

---

## 2 — Install system dependencies

```bash
# Python 3.11+
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Node.js 20 (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Nginx, git, ufw, certbot
apt install -y nginx git ufw python3-certbot-nginx

# PM2 (global)
npm install -g pm2
```

---

## 3 — Create the app user and directories

```bash
# Dedicated non-root user for the API service
useradd -r -m -s /bin/bash orator

# App directory
mkdir -p /opt/orator
chown orator:orator /opt/orator

# Data directory (SQLite DB + outputs)
mkdir -p /var/lib/orator/outputs
chown -R orator:orator /var/lib/orator

# Log directory
mkdir -p /var/log/orator
chown -R orator:orator /var/log/orator
```

---

## 4 — Clone the repository

```bash
cd /opt/orator
# Replace with your actual GitHub repo URL
git clone https://github.com/YOUR_ORG/orator.git .
chown -R orator:orator /opt/orator
```

---

## 5 — Python environment

```bash
cd /opt/orator
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

---

## 6 — Create the production `.env`

```bash
cp .env.example .env
nano .env          # or use your preferred editor
```

Set these values (at minimum):

```
ANTHROPIC_API_KEY=sk-ant-...
SITE_DOMAIN=orator.example.com
DB_PATH=/var/lib/orator/orator.db
OUTPUTS_DIR=/var/lib/orator/outputs
```

Secure the file:

```bash
chmod 600 .env
chown orator:orator .env
```

---

## 7 — Build the frontend

```bash
cd /opt/orator/web
npm ci                 # install exact lockfile deps
npm run build          # produces .next/ production build
cd /opt/orator
chown -R orator:orator web/.next
```

---

## 8 — Configure Nginx

```bash
# Replace YOUR_DOMAIN in the config
sed "s/YOUR_DOMAIN/$SITE_DOMAIN/g" /opt/orator/deploy/nginx.conf \
    > /etc/nginx/sites-available/orator

# Enable the site
ln -sf /etc/nginx/sites-available/orator /etc/nginx/sites-enabled/orator

# Remove the default placeholder
rm -f /etc/nginx/sites-enabled/default

# Test and reload
nginx -t && systemctl reload nginx
```

---

## 9 — Start the API with systemd

```bash
# Install the service unit
cp /opt/orator/deploy/orator-api.service /etc/systemd/system/

# Enable and start
systemctl daemon-reload
systemctl enable orator-api
systemctl start orator-api

# Verify
systemctl status orator-api
curl http://127.0.0.1:8000/docs        # should return FastAPI docs HTML
```

---

## 10 — Start the frontend with PM2

```bash
# Start the Next.js process
pm2 start /opt/orator/deploy/ecosystem.config.js

# Persist across reboots
pm2 save
pm2 startup systemd -u root --hp /root
# Run the command that pm2 prints

# Verify
curl http://127.0.0.1:3000             # should return HTML
```

---

## 11 — SSL with Certbot

```bash
# Obtain a certificate and auto-configure Nginx
certbot --nginx -d YOUR_DOMAIN

# Certbot will:
# 1. Obtain a Let's Encrypt certificate
# 2. Edit /etc/nginx/sites-available/orator to add the HTTPS server block
# 3. Add an HTTP→HTTPS redirect
# 4. Reload Nginx

# Verify auto-renewal (dry run)
certbot renew --dry-run
```

---

## 12 — Firewall

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'    # ports 80 + 443
ufw --force enable
ufw status
```

Ports 8000 and 3000 should remain closed to the internet — Nginx proxies to them
internally on 127.0.0.1.

---

## 13 — Verify end-to-end

```bash
# API health check via Nginx
curl https://YOUR_DOMAIN/api/docs        # FastAPI OpenAPI docs

# Frontend
curl -I https://YOUR_DOMAIN/            # should return 200
```

Open `https://YOUR_DOMAIN` in a browser. You should see the Orator landing page.

---

## Ongoing operations

### Deploy an update

```bash
ssh root@YOUR_VPS_IP
cd /opt/orator
git pull

# If Python deps changed:
.venv/bin/pip install -r requirements.txt

# If frontend changed:
cd web && npm ci && npm run build && cd ..

# Restart services
systemctl restart orator-api
pm2 restart orator-web
```

### View logs

```bash
# API logs
journalctl -u orator-api -f
tail -f /var/log/orator/api-error.log

# Frontend logs
pm2 logs orator-web

# Nginx access log
tail -f /var/log/nginx/access.log
```

### Check service status

```bash
systemctl status orator-api
pm2 status
nginx -t
```
