# Priya Broker Dashboard (Frontend)

React + TypeScript + Tailwind + TanStack Query + React Router. Talks only to the
existing Priya control-plane API (`priya.api`).

## Stack
- Vite + React 18 + TypeScript (strict)
- Tailwind CSS
- TanStack Query (server state, caching, loading/error states)
- React Router v6 (protected routes)

## Pages / Information architecture
- **Dashboard** — KPIs, live agent status, recent activity, campaign performance
- **Calls** — Live Calls · Call History (+ detail drawer) · Recordings · Transcripts
- **Campaigns** — Outbound Campaigns · Lead Lists · Scheduled Calls · multi-step wizard · results
- **AI Agent** — Agent Settings · Prompt Builder · Knowledge Base · Voice Settings · Call Flows
- **Appointments**, **Leads** (temperature-segmented + drawer), **Analytics**, **Settings** (Org · Phone · Integrations · Team · Billing)

## Design system
Tailwind-based: brand indigo/violet palette, soft shadows (`shadow-card`/`shadow-pop`),
rounded `2xl` cards, Inter type, inline `Icon` set, reusable kit (`StatCard`,
`Drawer`/`Modal`, `Badge`, `Button`, `ProgressBar`, `SubNav`, `ComingSoon`,
`EmptyState`). Light mode, mobile-responsive, no admin-template look.

## Data honesty (no invented endpoints)
Wired to real endpoints: Dashboard, Analytics, Calls, Campaigns (+ wizard/lifecycle/analytics),
Leads (CRUD/import/export), Knowledge Base (Properties CRUD), Appointments
(`/dashboard/summary`), Team (`/users`), Org (`/tenants/me`).

Features without a backend endpoint are shown as polished **"coming soon"**
surfaces (never fake data, never YAML/JSON): live call controls (listen/whisper/
take-over), call recordings, prompt/voice persistence, visual flow builder,
CRM integrations, buying numbers, and detailed billing.


## Auth
JWT is obtained from `POST /auth/login` (or `POST /auth/register`) and stored in
`localStorage`. Every request sends `Authorization: Bearer <token>`. A `401`
clears the token and bounces the user to `/login`. All data is tenant-scoped by
the API via the JWT; the UI additionally gates actions by role
(owner > admin > agent > viewer).

## Setup
```bash
cd frontend
cp .env.example .env      # optional; defaults work with the dev proxy
npm install
npm run dev               # http://localhost:5173
```

The dev server proxies `/api/*` to the backend (default `http://localhost:8080`,
override with `VITE_PROXY_TARGET`), so no backend CORS config is needed locally.

Start the backend separately:
```bash
uvicorn priya.api.main:app --reload --port 8080
```

## Build
```bash
npm run build     # type-checks then builds to dist/
npm run preview
```

## Production notes
- Set `VITE_API_BASE_URL` to the API origin, or serve the built `dist/` behind
  the same origin as the API (reverse proxy). If cross-origin, the API needs
  CORS enabled — the frontend does not add backend CORS config.

## Endpoint coverage
Uses only existing endpoints: `/auth/*`, `/tenants/me`, `/users*`, `/properties*`,
`/leads*` (incl. `/leads/import`, `/leads/export`), `/calls*`, `/dashboard/summary`,
`/analytics/*`, `/campaigns*`.

There is **no** `/appointments` list endpoint in the API, so the Appointments
page shows `DashboardSummary.recent_appointments` (the only tenant-scoped
appointment feed available). No endpoints were invented.
