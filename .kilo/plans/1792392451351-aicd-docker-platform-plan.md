# AICD Platform Plan

## Goal
Local Docker-Desktop based dev platform routed via Cloudflare Tunnel, with dynamic ingress (Traefik) and Cloudflare Access auth. Each component lives in its own folder with its own compose file; root compose orchestrates.

## Decisions
- Ingress: Traefik v3 (auto-discovers containers via Docker labels, hot-reloads without restart)
- Network: `AICD-net` (external Docker network created once)
- Tunnel: `cloudflared` container on AICD-net, routes hostname to Traefik
- TLS: Cloudflare edge TLS only; internal AICD-net traffic is HTTP
- Auth: Cloudflare Access (Zero Trust) in front of the tunnel hostname
- Domain: include Cloudflare domain/DNS onboarding steps

## Directory Layout
```
AICD/
├── .env (from sample.env)
├── docker-compose.yml          # root orchestrator
├── network/
│   └── create-network.sh       # docker network create AICD-net
├── tunnel/
│   ├── docker-compose.yml
│   └── config.yml              # cloudflared ingress rules
├── ingress/
│   ├── docker-compose.yml      # Traefik
│   └── traefik.yml             # static config
├── components/                 # each new component folder
│   └── <name>/
│       ├── docker-compose.yml
│       └── .env (optional)
└── sample.env
```

## Root Orchestration
Root `docker-compose.yml` uses `include` (compose v2.20+) to pull each component compose, so adding a component = add include entry + folder. Alternatively a `docker-compose.override.yml` merge; recommend `include` for clarity.

## Dynamic Ingress Pattern
Each component declares Traefik labels in its compose:
```
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.<name>.rule=Host(`<name>.${DOMAIN}`)"
  - "traefik.http.routers.<name>.entrypoints=web"
  - "traefik.http.services.<name>.loadbalancer.server.port=<port>"
```
Traefik watches Docker socket (read-only) and registers routes live. No restart needed.

## Cloudflare Tunnel Config
`config.yml`:
```
tunnel: ${CF_TUNNEL_ID}
credentials-file: /etc/cloudflared/creds.json
ingress:
  - hostname: ${DOMAIN}
    service: http://traefik:80
  - service: http_status:404
```
Cloudflare Access policy applied to `${DOMAIN}` (and `*.${DOMAIN}` if wildcard) in Zero Trust dashboard.

## sample.env
```
DOMAIN=example.com
CF_TUNNEL_ID=
CF_TUNNEL_TOKEN=
TRAEFIK_DASHBOARD_USER=admin
TRAEFIK_DASHBOARD_PASS=changeme
```

## Setup Steps
1. Create `AICD-net`: `docker network create AICD-net`
2. Copy `sample.env` -> `.env`, fill values
3. Cloudflare: add domain, create tunnel, download creds, set Access policy
4. `docker compose up -d` from root
5. Verify tunnel status + Traefik dashboard

## Adding a Component
1. Create `components/<name>/docker-compose.yml` with service on `AICD-net` + Traefik labels
2. Add include entry in root compose
3. `docker compose up -d <name>`; route appears automatically

## Security
- Cloudflare Access protects public hostname (email/IdP allowlist)
- Traefik dashboard behind basic auth or disabled in prod
- Docker socket mounted read-only to Traefik
- No component ports published to host except tunnel (optional admin ports bound to 127.0.0.1)

## Validation
- `docker compose config` validates merged config
- `curl -I https://${DOMAIN}` returns 302 to Cloudflare Access login
- After auth, component route responds 200
- Add test component and confirm route appears without Traefik restart

## Risks
- Cloudflare tunnel single point of failure; consider redundant tunnel (out of scope v1)
- Docker socket access is powerful; restrict to Traefik only
- Domain onboarding requires manual Cloudflare steps

## Open Questions
- Wildcard hostname vs per-component subdomains? (recommend subdomains)
- Should components expose admin ports locally? default no
