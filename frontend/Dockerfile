# syntax=docker/dockerfile:1
# =========================================================================
# Broker dashboard — build the Vite app, serve it via Caddy with AUTOMATIC
# HTTPS (Let's Encrypt), and reverse-proxy /api -> the FastAPI container.
# Single origin (https://<your-domain>) => no CORS needed.
# =========================================================================
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
# VITE_API_BASE_URL=/api is the default in src/lib/api.ts; the SPA calls the
# same origin and Caddy proxies /api to the API service.
RUN npm run build

FROM caddy:2.8-alpine AS serve
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80 443
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
