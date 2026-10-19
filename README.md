# AICD - AI Cloud Data Platform

Local Docker-Desktop dev platform routed via Cloudflare Tunnel with Traefik dynamic ingress and Cloudflare Access authentication.

## Overview

- **Ingress**: Traefik `3.7.15` (auto-discovers containers via Docker labels)
- **Tunnel**: Cloudflare Zero Trust Tunnel (`cloudflare/cloudflared:2026.10.1`) routes `dev.akashatek.com` to Traefik on Docker Desktop
- **Auth**: Cloudflare Access (Zero Trust) protects `dev.akashatek.com` and all `*.dev.akashatek.com` routes
- **Test server**: NGINX `1.31.7-alpine` exposed on port 80 internally on `AICD-net`
- **Network**: All containers on `AICD-net` Docker network
- **TLS**: Handled at Cloudflare edge; internal traffic is HTTP
- **Images pinned**: traefik:3.7.15, cloudflare/cloudflared:2026.10.1, nginx:1.31.7-alpine
- **Public site**: `akashatek.com` and `blog.akashatek.com` routed to `https://akashatek.infinityfreeapp.com/`

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose v2.20+
- Domain `akashatek.com` managed by [Squarespace](https://domains.squarespace.com/) (nameservers ns-cloud-*.googledomains.com / Squarespace DNS)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/) access (free tier OK)

## 1) Cloudflare Tunnel Setup (dev.akashatek.com)

Since `akashatek.com` is managed by Squarespace/Google, you do **not** need to move nameservers. Route only `dev.akashatek.com` via Cloudflare Tunnel using a CNAME in Squarespace DNS.

### Step 1: Create Cloudflare Tunnel
1. Go to [Cloudflare Zero Trust > Networks > Tunnels](https://one.dash.cloudflare.com/?to=/:account/networks/tunnels)
2. **Create a tunnel** > **Cloudflared**
3. Name: `aicd-dev`
4. Copy the **Tunnel Token** (`CF_TUNNEL_TOKEN`) — this must be a **Named Tunnel** token
5. Open tunnel details, copy **Tunnel ID** (`CF_TUNNEL_ID`)

### Step 2: Configure public hostname
1. Tunnel > **Public Hostname** > Add a public hostname
2. **Subdomain**: `dev`
3. **Domain**: select a domain already on Cloudflare (or add `akashatek.com` as a zone in Cloudflare without changing NS)
4. **Service Type**: `HTTP`
5. **URL**: `http://traefik:80` (points to Traefik via tunnel)
6. Save. Cloudflare shows the CNAME target (e.g. `<tunnel-id>.cfargotunnel.com`)

### Step 3: Squarespace DNS - CNAME dev.akashatek.com
1. Go to Squarespace Domains > your domain > **DNS Settings**
2. Add record:
   - **Type**: `CNAME`
   - **Host**: `dev`
   - **Data**: `<tunnel-id>.cfargotunnel.com` (the target from Step 2)
   - **TTL**: default/automatic
3. Save. No proxy toggle needed (it's DNS only).

### Step 4: Squarespace DNS - akashatek.com & blog.akashatek.com to InfinityFree
In Squarespace DNS Settings:

- **akashatek.com** (apex): add `A` record(s) pointing to InfinityFree's IP if provided, OR use Squarespace **URL forwarding** (Settings > Domain > Forwarding) to `https://akashatek.infinityfreeapp.com/` if available.
- **blog.akashatek.com**: add `CNAME` record `blog` -> `akashatek.infinityfreeapp.com` (if InfinityFree accepts CNAME) or an `A` record to InfinityFree IP.

If InfinityFree only provides a URL and not an IP/CNAME target, use Cloudflare Redirect Rules (delegate full zone to Cloudflare) or handle redirects at InfinityFree's end.

### Step 5: (Optional) Cloudflare Access to protect dev.*
If you want password/auth protection on `dev.akashatek.com`:
1. [Zero Trust > Access > Applications](https://one.dash.cloudflare.com/?to=/:account/access/apps) > Add Self-hosted
2. Hostnames: `dev.akashatek.com`, `*.dev.akashatek.com`
3. Add allow policy for your email/users
4. Save

## 2) Start Tunnel, Traefik & Test Server

### Step 1: Configure environment
```bash
cd /Users/heibalvin/Github/heibalvin/AICD
cp sample.env .env
```

Edit `.env`:
```bash
DOMAIN=dev.akashatek.com
CF_TUNNEL_ID=<YOUR_TUNNEL_ID>
CF_TUNNEL_TOKEN=<YOUR_TUNNEL_TOKEN>
TRAEFIK_DASHBOARD_USER=<YOUR_DASHBOARD_USER>
TRAEFIK_DASHBOARD_PASS=<YOUR_DASHBOARD_PASS>
```

### Step 2: Start services
```bash
docker compose up -d
docker compose ps
docker compose logs -f cloudflared
docker compose logs -f traefik
```

### Step 4: Test locally
```bash
curl -I https://dev.akashatek.com/test
curl -I https://dev.akashatek.com/test
```
Should return NGINX welcome page (200 OK) — note test NGINX is exposed internally on port 80 via Traefik, not published to host.

### Step 5: Test via tunnel
```bash
dig dev.akashatek.com CNAME +short
curl -I https://dev.akashatek.com
```

### Step 6: Traefik dashboard
- Local: http://localhost:8080 (127.0.0.1 only)
- Via tunnel: https://dev.akashatek.com/traefik (behind Cloudflare Access if enabled)

## 3) Images (pinned)

| Service | Image |
|---|---|
| traefik | traefik:3.7.15 |
| cloudflared | cloudflare/cloudflared:2026.10.1 |
| test nginx | nginx:1.31.7-alpine |

## 4) Squarespace + Google Domain Summary

| Host | Record | Target | Notes |
|---|---|---|---|
| `dev` | CNAME | `<tunnel-id>.cfargotunnel.com` | Cloudflare Tunnel -> Traefik |
| `akashatek.com` | A / Forwarding | InfinityFree IP / URL | Public site |
| `blog` | CNAME / A | InfinityFree target | Public site |

## Troubleshooting

| Issue | Fix |
|---|---|
| `Provided Tunnel token is not valid` | Use a **Named Tunnel** token (not quick-tunnel). Check `CF_TUNNEL_TOKEN` has no spaces/quotes; regenerate in Cloudflare Tunnel UI |
| Tunnel won't connect | `docker compose logs cloudflared`; verify token valid; network `AICD-net` exists |
| Traefik not starting | `docker compose logs traefik`; verify `/var/run/docker.sock` accessible; check `traefik.yml` |
| `dev.akashatek.com` doesn't resolve | Wait for Squarespace DNS propagation; verify CNAME points to cfargotunnel.com |
| Port 8080 conflict | Free local `:8080` before starting traefik |
| 404 via tunnel | Verify tunnel Public Hostname URL points to `http://traefik:80`; test service has Traefik labels |

## Validation Checklist

- [ ] `.env` copied from `sample.env` with tunnel ID/token and Traefik auth
- [ ] `docker compose up -d` starts cloudflared + traefik + test (network `AICD-net` defined in root compose)
- [ ] `curl http://localhost:8080` reaches Traefik dashboard locally
- [ ] `dig dev.akashatek.com CNAME` shows tunnel target
- [ ] `curl -I https://dev.akashatek.com` responds (200 or Access redirect)
- [ ] `https://dev.akashatek.com/traefik` reachable after Access auth
