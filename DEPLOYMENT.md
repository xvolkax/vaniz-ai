# Priya — Production Deployment (DigitalOcean)

Target: **DigitalOcean Ubuntu 22.04 droplet** in **blr1 (Bangalore)** or
**sgp1 (Singapore)** for lowest latency to Indian callers.

The platform runs five services: the **agent worker**, the **control-plane API**
(JWT, multi-tenant), the **dashboard** (Caddy edge with automatic HTTPS),
**PostgreSQL**, and a one-shot **migrate** job.

> **Recommended path:** the full-stack Docker + Caddy flow with a domain and
> automatic HTTPS — see **Section 8**. Sections 0–7 below cover the underlying
> pieces (Docker Compose / systemd) and apply to both paths.

---

## 0. Prerequisites

- LiveKit project (Cloud or self-hosted) → `LIVEKIT_URL`, key, secret.
- Vobiz virtual number + SIP credentials.
- API keys: Deepgram/Sarvam, OpenAI, Cartesia.
- A **domain** (e.g. `vaniz.in`) with A records pointed at the droplet — used by
  Caddy for automatic HTTPS and served on one origin (dashboard + `/api`).
- A strong **`JWT_SECRET`** (control-plane auth) and **`POSTGRES_PASSWORD`**.

Recommended droplet: 2–4 vCPU / 4–8 GB (CPU-optimized) to start; scale on
`priya_active_calls` + CPU.

---

## 1. Provision the droplet

```bash
# On a fresh droplet as root:
apt-get update && apt-get install -y git
git clone <your-repo-url> /opt/priya
cd /opt/priya
bash deploy/digitalocean_setup.sh      # installs Docker + ufw (opens 80/443)
```

Configure secrets:

```bash
cp deploy/env.production.template .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # -> JWT_SECRET
nano .env
```

Set at minimum: `SITE_ADDRESS` + `ACME_EMAIL` (domain/HTTPS), a strong
`POSTGRES_PASSWORD` and matching `DATABASE_URL`, `JWT_SECRET`, `SERVICE_REGION`,
and the LiveKit / Vobiz / STT-LLM-TTS credentials. Keep `KNOWLEDGE_SOURCE=db`.
Leave `ALLOW_PUBLIC_SIGNUP=true` until the first tenant is created (Section 8.6).

---

## 2. Provision Vobiz SIP (once)

```bash
# Run inside a container so deps are present:
docker compose run --rm agent python scripts/setup_sip.py
```

Copy the printed IDs into `.env`:

```
SIP_INBOUND_TRUNK_ID=ST_xxx
SIP_OUTBOUND_TRUNK_ID=ST_yyy
SIP_DISPATCH_RULE_ID=SDR_zzz
```

In the Vobiz portal, point your virtual number's SIP termination at your LiveKit
SIP URI (from the LiveKit project's SIP settings). Inbound calls will now be
dispatched to `agent_name=priya-agent` via the dispatch rule.

---

## 3A. Deploy with Docker Compose (recommended)

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f web api agent
```

Services:
- `postgres` — data store (volume `pgdata`).
- `migrate` — runs `alembic upgrade head` once (creates tenants, users,
  properties, leads, calls, campaigns, … ), then exits.
- `agent` — the LiveKit worker (scale with `--scale agent=N`).
- `api` — FastAPI control plane, bound to `127.0.0.1:8080` (reached via the web proxy).
- `web` — Caddy edge: serves the dashboard SPA + proxies `/api` → `api:8080`,
  with automatic HTTPS for `SITE_ADDRESS`. Public on `:80` + `:443`.

> The full-stack one-command flow is `bash deploy/deploy_fullstack.sh`
> (build → migrate → up). See Section 8.

Scale workers for concurrency:

```bash
docker compose up -d --scale agent=3
```

---

## 3B. Deploy with systemd (bare metal alternative)

```bash
# Python env
apt-get install -y python3-venv
python3 -m venv /opt/priya/.venv
/opt/priya/.venv/bin/pip install -r /opt/priya/requirements.txt
/opt/priya/.venv/bin/python -m priya.agent.worker download-files

# Create the runtime user + DB (managed Postgres or local)
useradd --system --create-home priya || true
chown -R priya:priya /opt/priya
/opt/priya/.venv/bin/alembic upgrade head

# Install services
cp deploy/systemd/priya-agent.service /etc/systemd/system/
cp deploy/systemd/priya-api.service   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now priya-agent priya-api
systemctl status priya-agent priya-api
```

Scale workers with a templated unit (copy `priya-agent.service` to
`priya-agent@.service` and `systemctl enable --now priya-agent@{1,2,3}`).

---

## 4. TLS / edge

For the **Docker path (recommended)**, TLS is handled automatically by the
`web` Caddy service — no manual nginx/certbot. Just set `SITE_ADDRESS` +
`ACME_EMAIL` in `.env` and point DNS at the droplet (Section 8).

For the **bare-metal path (systemd)**, front the API + dashboard with host nginx
and certbot using `deploy/nginx/priya-dashboard.conf` (serves the built SPA and
proxies `/api` → `127.0.0.1:8080`). See Section 8.9. The voice/SIP media path
goes **directly to LiveKit** — the edge only fronts the dashboard + API.

---

## 5. Verify

```bash
curl https://vaniz.in/api/healthz     # {"status":"ok",...}
curl https://vaniz.in/api/readyz       # checks DB connectivity

# Control-plane auth is JWT + multi-tenant. Register the first org (or log in),
# then use the returned token. Disable ALLOW_PUBLIC_SIGNUP afterwards (8.6).
TOKEN=$(curl -s -X POST https://vaniz.in/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@acme.com","password":"your-password"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Place a test outbound call (tenant-scoped via the JWT):
curl -X POST https://vaniz.in/api/calls/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"+9198XXXXXXXX","lead_name":"Test"}'
```

Or just open **https://vaniz.in/** and use the dashboard.

Call an inbound test to your Vobiz number and confirm Priya greets in Hindi.
Check a `calls` row and `conversation_summaries` row are written, and that
`/metrics` counters (`priya_calls_total`, `priya_*_latency_seconds`) update.

---

## 6. Monitoring

- Scrape `https://api.your-domain.com/metrics` with Prometheus (restricted to
  your monitoring subnet in `deploy/nginx/priya.conf`).
- Key metrics: `priya_active_calls`, `priya_e2e_latency_seconds`,
  `priya_interruptions_total`, `priya_leads_qualified_total`,
  `priya_appointments_booked_total`, `priya_calls_total{outcome=...}`.
- Logs are structured JSON (structlog) — ship to your log stack; correlate on
  `call_id`.

---

## 7. Operations

- **Rolling update**: `git pull && docker compose up -d --build`. In-flight calls
  drain on `SIGTERM` (30s stop timeout; finalization is guaranteed idempotently).
- **Migrations**: `docker compose run --rm migrate` (or `alembic upgrade head`).
- **Backups**: snapshot the `pgdata` volume / use DO Managed Postgres automated
  backups.
- **Secrets rotation**: update `.env` and restart services. Never commit `.env`.

---

## 8. Full-stack deploy (dashboard + API + agent) with a domain + HTTPS

This serves the **broker dashboard** and the **API** on one origin with
**automatic HTTPS** (Let's Encrypt via Caddy) at your domain (example:
`vaniz.in`). The dashboard calls `/api`, which Caddy proxies to the API
container — so there is **no CORS** to configure.

Topology (all in `docker-compose.yml`):
- `web` (Caddy) — public on **:80 + :443**, auto-TLS for `$SITE_ADDRESS`,
  serves the built dashboard + proxies `/api` → `api:8080`.
- `api` — bound to `127.0.0.1:8080` (reachable only via the `web` proxy / localhost).
- `agent` — LiveKit voice worker (scale with `--scale agent=N`).
- `postgres` + `migrate` — data store and one-shot migrations.

### 8.0 DNS (do this first — TLS depends on it)
Point your domain at the droplet IP `168.144.208.3`:

| Type | Host | Value           |
|------|------|-----------------|
| A    | @    | 168.144.208.3   |
| A    | www  | 168.144.208.3   |

Wait for propagation: `dig +short vaniz.in` should return `168.144.208.3`.

### 8.1 Provision + fetch code
```bash
# On a fresh Ubuntu 22.04 droplet as root:
apt-get update && apt-get install -y git
git clone <your-repo-url> /opt/priya
cd /opt/priya
bash deploy/digitalocean_setup.sh      # Docker + ufw (allows 80/443)
```

### 8.2 Configure secrets + domain
```bash
cp deploy/env.production.template .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # -> JWT_SECRET
nano .env
#   SITE_ADDRESS=vaniz.in www.vaniz.in
#   ACME_EMAIL=you@vaniz.in
#   DB password, JWT_SECRET, LiveKit, STT/LLM/TTS, Vobiz ...
```

### 8.3 (Once) Provision Vobiz SIP trunks
```bash
docker compose run --rm agent python scripts/setup_sip.py
# paste SIP_INBOUND_TRUNK_ID / SIP_OUTBOUND_TRUNK_ID / SIP_DISPATCH_RULE_ID into .env
```

### 8.4 Build + launch everything
```bash
bash deploy/deploy_fullstack.sh
```
Caddy will automatically obtain and renew the TLS certificate on first start
(needs ports 80/443 reachable and DNS pointing at the droplet).

### 8.5 Verify
```bash
curl https://vaniz.in/api/healthz      # {"status":"ok",...}
curl https://vaniz.in/api/readyz        # DB connectivity
# Open the dashboard:  https://vaniz.in/
```
In the dashboard, click **Create one** to register your first organization
(tenant + owner user). Then add properties, leads, and campaigns.

### 8.6 Lock down signup
After the first tenant is created, disable public signup:
```bash
sed -i 's/^ALLOW_PUBLIC_SIGNUP=.*/ALLOW_PUBLIC_SIGNUP=false/' .env
docker compose up -d --build web api
```

### 8.7 Migrate existing project.yaml into a tenant (optional)
If you were running the single-tenant YAML flow, seed a tenant + its properties:
```bash
docker compose run --rm api python scripts/migrate_yaml_to_db.py \
  --slug my-brokerage --owner-email owner@example.com \
  --owner-password 'ChangeThis123' --phone +91XXXXXXXXXX
```

### 8.8 TLS notes
- Certificates are issued/renewed automatically by Caddy and persist in the
  `caddy_data` volume across restarts.
- To run on the IP without a domain temporarily, set `SITE_ADDRESS=:80` in
  `.env` (plain HTTP, no cert). Switch to your domain once DNS is ready.
- Firewall is already open on 80/443 (`digitalocean_setup.sh`).

### 8.9 Bare-metal alternative (systemd + host nginx)
If you prefer not to containerize the web tier:
1. Follow **3B** (systemd) for `api` + `agent`.
2. Build the dashboard and publish it:
   ```bash
   cd frontend && npm install && npm run build
   sudo mkdir -p /var/www/priya-dashboard
   sudo cp -r dist/* /var/www/priya-dashboard/
   ```
3. Install the host nginx site + TLS:
   ```bash
   sudo cp deploy/nginx/priya-dashboard.conf /etc/nginx/sites-available/priya-dashboard
   # set server_name to vaniz.in www.vaniz.in in the file
   sudo ln -s /etc/nginx/sites-available/priya-dashboard /etc/nginx/sites-enabled/
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d vaniz.in -d www.vaniz.in
   sudo nginx -t && sudo systemctl reload nginx
   ```

### 8.10 Common operations
```bash
docker compose logs -f web api agent     # tail logs
docker compose up -d --scale agent=3      # scale voice workers
git pull && bash deploy/deploy_fullstack.sh   # rolling update (calls drain on SIGTERM)
```
