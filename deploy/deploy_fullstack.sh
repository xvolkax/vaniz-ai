#!/usr/bin/env bash
# =========================================================================
# Full-stack deploy on the droplet: postgres + migrate + agent + api + web.
# Run from the repo root on the droplet (as a user in the `docker` group):
#     bash deploy/deploy_fullstack.sh
# =========================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Run: cp deploy/env.production.template .env && nano .env"
  exit 1
fi

echo ">> Building images (agent/api share one image; web builds the dashboard)"
docker compose build

echo ">> Applying DB migrations (one-shot)"
docker compose run --rm migrate

echo ">> Starting services"
docker compose up -d

echo ">> Status"
docker compose ps

IP="$(curl -fsSL ifconfig.me 2>/dev/null || echo 'YOUR_DROPLET_IP')"
cat <<EOF

Deploy complete.
  Dashboard:  http://${IP}/
  API (proxied via nginx): http://${IP}/api/healthz

Next:
  * Open the dashboard, click "Create one" to register your first tenant.
  * After registering, set ALLOW_PUBLIC_SIGNUP=false in .env and:
        docker compose up -d --build web api
  * Scale voice workers for concurrency:  docker compose up -d --scale agent=3
EOF
