#!/usr/bin/env bash
# =========================================================================
# Priya Voice Agent — DigitalOcean Ubuntu 22.04 provisioning (Docker path)
# Region: blr1 (Bangalore) or sgp1 (Singapore) for lowest latency to Indian
# callers and to Deepgram/OpenAI/Cartesia edge PoPs.
# Run as root on a fresh droplet:  bash digitalocean_setup.sh
# =========================================================================
set -euo pipefail

echo ">> Updating system packages"
apt-get update && apt-get upgrade -y

echo ">> Installing Docker + Compose plugin"
apt-get install -y ca-certificates curl gnupg ufw
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo ">> Configuring firewall (SSH + HTTPS only; media goes to LiveKit directly)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ">> Creating app directory"
mkdir -p /opt/priya
cd /opt/priya

echo ">> Next steps:"
cat <<'EOF'
  Full-stack deploy (dashboard + API + agent, Docker + auto-HTTPS via Caddy):
    1. Point DNS: A record  vaniz.in -> this droplet IP (and www).
    2. Copy the project to /opt/priya (git clone or scp).
    3. cp deploy/env.production.template .env  &&  edit .env
         (set SITE_ADDRESS, ACME_EMAIL, DB password, JWT_SECRET, LiveKit, Vobiz...)
    4. docker compose run --rm agent python scripts/setup_sip.py
         (paste the returned SIP IDs into .env)
    5. bash deploy/deploy_fullstack.sh
    6. Verify:  curl https://vaniz.in/api/readyz   and open  https://vaniz.in/

  See DEPLOYMENT.md section 8 for the full walkthrough. (Host nginx is NOT
  installed here — the dockerized Caddy `web` service binds 80/443. Install
  nginx manually only if you use the bare-metal alternative in section 8.9.)
EOF
echo ">> Base provisioning complete."
