# AICD - AI Cloud Data Platform

Local Docker-Desktop based dev platform routed via Cloudflare Tunnel with Traefik dynamic ingress and Cloudflare Access authentication.

## Overview

- **Ingress**: Traefik v3.5.3 (auto-discovers containers via Docker labels)
- **Tunnel**: Cloudflare Zero Trust Tunnel (cloudflared 2025.10.0) routes `dev.akashatek.com` to Traefik on Docker Desktop
- **Auth**: Cloudflare Access (Zero Trust) protects `dev.akashatek.com` and all `*.dev.akashatek.com` routes
- **Network**: All containers on `AICD-net` Docker network
- **TLS**: Handled at Cloudflare edge; internal traffic is HTTP
- **Images pinned**: traefik:v3.5.3, cloudflare/cloudflared:2025.10.0, nginx:1.29.2-alpine
- **Public site**: `akashatek.com` and `blog.akashatek.com` redirected to `https://akashatek.infinityfreeapp.com/`

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose v2.20+
- Domain `akashatek.com` managed by [Cloudflare](https://www.cloudflare.com/)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/) access

## 1) Cloudflare DNS, Tunnel, SSL & Access Setup

### Step 1: Ensure domain is on Cloudflare
1. Login to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Confirm `akashatek.com` is active on Cloudflare (nameservers pointing to Cloudflare)
3. Keep DNS proxying enabled ("orange cloud") where appropriate

### Step 2: Redirect akashatek.com & blog.akashatek.com to your public page
Use Cloudflare **Rules > Redirect Rules**:

1. Go to [Cloudflare Dashboard > Rules > Redirect Rules](https://dash.cloudflare.com/?to=/:account/:zone/rules/redirect-rules)
2. Create rule: "Redirect root & blog to InfinityFree"
3. Match: `Hostname equals akashatek.com OR Hostname equals blog.akashatek.com`
4. Redirect to: `https://akashatek.infinityfreeapp.com/$1` (preserve query string)
5. Status: 301 Permanent Redirect
6. Deploy

### Step 3: Create Zero Trust Tunnel for dev.akashatek.com
1. Go to [Cloudflare Zero Trust > Networks > Tunnels](https://one.dash.cloudflare.com/?to=/:account/networks/tunnels)
2. Click **Create a tunnel** > **Cloudflared**
3. Name: `aicd-dev`
4. Copy the **Tunnel Token** (use for `CF_TUNNEL_TOKEN`)
5. After creation, open tunnel details and copy **Tunnel ID** (use for `CF_TUNNEL_ID`)

### Step 4: Set public hostname for the tunnel
1. Tunnel > **Public Hostname** > **Add a public hostname**
2. Subdomain: `dev`
3. Domain: `akashatek.com`
4. Service Type: `HTTP`
5. URL: `traefik:80`
6. Save

### Step 5: Cloudflare Access (protect dev.*)
1. Go to [Zero Trust > Access > Applications](https://one.dash.cloudflare.com/?to=/:account/access/apps)
2. Add application > **Self-hosted**
3. Name: `AICD Dev Platform`
4. Public hostnames: `dev.akashatek.com`, `*.dev.akashatek.com`
5. Identity providers: configure as desired
6. Policy: allow your users/emails
7. Save

## 2) Start Tunnel & Traefik

### Step 1: Configure environment
```bash
cd /Users/heibalvin/Github/heibalvin/AICD
cp sample.env .env
```

Edit `.env`:
```bash
DOMAIN=dev.akashatek.com
CF_TUNNEL_ID=your-tunnel-id
CF_TUNNEL_TOKEN=your-tunnel-token
TRAEFIK_DASHBOARD_USER=admin
TRAEFIK_DASHBOARD_PASS=your-secure-password
```

### Step 2: Tunnel authentication
This stack uses token auth via `CF_TUNNEL_TOKEN`. `tunnel/docker-compose.yml` also mounts `~/.cloudflared/creds.json:ro`. If you downloaded `creds.json` from Cloudflare, place it at `~/.cloudflared/creds.json`. If using only the token, it's fine to leave that file absent.

### Step 3: Create network
```bash
./network/create-network.sh
# or: docker network create AICD-net
```

### Step 4: Start services
```bash
docker compose up -d
docker compose ps
docker compose logs -f tunnel
docker compose logs -f ingress
```

### Step 5: Traefik dashboard
- Local: http://localhost:8080 (127.0.0.1 only)
- Via tunnel: https://traefik.dev.akashatek.com (behind Cloudflare Access if enabled)

## 3) Add NGINX Component & Routing Rules

Components live under `components/<name>/`. Root `docker-compose.yml` uses `include`.

Example:
```bash
mkdir -p components/my-app/html
cat > components/my-app/docker-compose.yml << 'YML'
services:
  my-app:
    image: nginx:1.29.2-alpine
    container_name: aicd-my-app
    restart: unless-stopped
    networks:
      - aicd-net
    volumes:
      - ./html:/usr/share/nginx/html:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.my-app.rule=Host(`my-app.dev.akashatek.com`)"
      - "traefik.http.routers.my-app.entrypoints=web"
      - "traefik.http.services.my-app.loadbalancer.server.port=80"

networks:
  aicd-net:
    external: true
    name: AICD-net
YML
echo "<h1>My App</h1>" > components/my-app/html/index.html
```

Add to root `docker-compose.yml` includes:
```yaml
  - components/my-app/docker-compose.yml
```

Start:
```bash
docker compose up -d my-app
```

Routes appear automatically.

Pre-configured: `test.dev.akashatek.com` (Traefik) and `http://localhost:80` (local-only).

## 4) Test Everything

```bash
# Local
curl -I http://localhost:80
curl http://localhost:8080

# Health
docker compose logs tunnel --tail=20
docker compose logs ingress --tail=20
docker compose config --services
docker compose ps

# Public
curl -I https://akashatek.com
curl -I https://blog.akashatek.com
curl -I https://dev.akashatek.com
curl -I https://traefik.dev.akashatek.com
curl -I https://test.dev.akashatek.com
```

After Access auth, `dev.akashatek.com` routes return 200.

## Troubleshooting

| Issue | Solution |
|---|---|
| Network missing | `./network/create-network.sh` or `docker network create AICD-net` |
| Tunnel fails | Verify `CF_TUNNEL_ID`/`CF_TUNNEL_TOKEN` or `~/.cloudflared/creds.json`; `docker compose logs tunnel` |
| 404 on `*.dev.akashatek.com` | Ensure public hostname `dev.akashatek.com` points to `http://traefik:80`; DNS proxied (orange cloud) |
| Not routing | Check Traefik labels + container on `AICD-net`; `docker compose logs ingress` |
| Access loop | Confirm user in Access policy |
| Port 80 conflict | Free `:80` or `docker compose stop http-test` |

## Validation Checklist

- [ ] `akashatek.com`/`blog.akashatek.com` redirect to InfinityFree
- [ ] `dev.akashatek.com` public hostname -> `http://traefik:80` in Cloudflare Tunnel
- [ ] Access protects `dev.akashatek.com` and `*.dev.akashatek.com`
- [ ] `.env` has `DOMAIN=dev.akashatek.com` and tunnel creds
- [ ] Stack up: tunnel + traefik + test/http-test healthy
- [ ] `https://traefik.dev.akashatek.com`/`https://test.dev.akashatek.com` reachable after auth
- [ ] `http://localhost:80` serves test page
- [ ] New component auto-registers
- [ ] `docker compose config` validates
