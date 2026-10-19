# AICD - AI Cloud Data Platform

Local Docker-Desktop based dev platform routed via Cloudflare Tunnel with Traefik dynamic ingress and Cloudflare Access authentication.

## Overview

- **Ingress**: Traefik v3 (auto-discovers containers via Docker labels)
- **Tunnel**: Cloudflare Tunnel (cloudflared) routes public traffic to Traefik
- **Auth**: Cloudflare Access (Zero Trust) protects public hostname
- **Network**: All containers on `AICD-net` Docker network
- **TLS**: Handled at Cloudflare edge; internal traffic is HTTP

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose v2.20+
- A domain managed by [Cloudflare](https://www.cloudflare.com/)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/) access to your account

## 1) Setup Cloudflare, SSL Authentication & DNS

### Step 1: Add your domain to Cloudflare
1. Login to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Add your domain `yourdomain.com` (use your actual domain)
3. Update nameservers at your registrar to point to Cloudflare's nameservers
4. Wait for DNS to propagate (usually a few minutes)

### Step 2: Create a Cloudflare Tunnel
1. Go to [Zero Trust > Tunnels](https://one.dash.cloudflare.com/) > Create a tunnel
2. Select "Cloudflared" as the connector type
3. Name your tunnel (e.g., `aicd-dev`)
4. Copy the tunnel token shown (you'll need this for `CF_TUNNEL_TOKEN`)
5. Save the tunnel and note the Tunnel ID (shown in tunnel details)

### Step 3: Configure DNS for the tunnel
1. In your tunnel settings, go to "Public Hostname" > Add a public hostname
2. Subdomain: `*` (wildcard) or specific subdomains like `test`, `traefik`
3. Domain: select your domain
4. Service Type: `HTTP`
5. URL: `traefik:80` (internal Traefik service)
6. Save the configuration

This routes all `*.yourdomain.com` requests through the tunnel to Traefik.

### Step 4: Setup Cloudflare Access (Authentication)
1. Go to [Zero Trust > Access > Applications](https://one.dash.cloudflare.com/) > Add an application
2. Select "Self-hosted"
3. Application name: `AICD Platform`
4. Session duration: choose based on your needs (e.g., 24 hours)
5. Public hostname: `yourdomain.com` and/or `*.yourdomain.com` 
6. Identity providers: Configure your preferred IdP (Google, GitHub, email, etc.)
7. Policy: Create an allow policy - add allowed emails/groups
8. Save the application

## 2) Start the Tunnel & Traefik

### Step 1: Clone and configure environment
```bash
# Navigate to project directory
cd /path/to/AICD

# Copy sample environment file
cp sample.env .env

# Edit .env with your values
nano .env  # or your preferred editor
```

Update the following values in `.env`:
```bash
DOMAIN=yourdomain.com
CF_TUNNEL_ID=your-tunnel-id
CF_TUNNEL_TOKEN=your-tunnel-token
TRAEFIK_DASHBOARD_USER=admin
TRAEFIK_DASHBOARD_PASS=your-secure-password
```

### Step 2: Setup Cloudflare credentials file (for tunnel config)
Cloudflared can authenticate via token (we pass it via env), or via credentials file. For the mounted `creds.json`, either:
- Download it from tunnel setup page and save to `~/.cloudflared/creds.json`
- Or generate it after tunnel creation

The tunnel compose mounts: `~/.cloudflared/creds.json:/etc/cloudflared/creds.json:ro`

### Step 3: Create Docker network
```bash
./network/create-network.sh
# or: docker network create AICD-net
```

### Step 4: Start services
From the project root:
```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f tunnel
docker compose logs -f ingress
```

### Step 5: Verify Traefik dashboard
- **Locally**: http://localhost:8080 (only accessible from localhost)
- **Via tunnel**: https://traefik.yourdomain.com (requires Cloudflare Access auth if enabled)

Login with `TRAEFIK_DASHBOARD_USER` and `TRAEFIK_DASHBOARD_PASS` from `.env`.

## 3) Add NGINX Component & Routing Rules

### Adding a new component with routing

Each component lives in its own folder under `components/<name>/` with its own `docker-compose.yml`. The root `docker-compose.yml` uses `include` to orchestrate everything.

#### Example: Add an NGINX service

1. Create component directory:
```bash
mkdir -p components/my-app
```

2. Create `components/my-app/docker-compose.yml`:
```yaml
services:
  my-app:
    image: nginx:alpine
    container_name: aicd-my-app
    restart: unless-stopped
    networks:
      - aicd-net
    volumes:
      - ./html:/usr/share/nginx/html:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.my-app.rule=Host(`my-app.${DOMAIN}`)"
      - "traefik.http.routers.my-app.entrypoints=web"
      - "traefik.http.services.my-app.loadbalancer.server.port=80"

networks:
  aicd-net:
    external: true
    name: AICD-net
```

3. Add content (optional):
```bash
mkdir -p components/my-app/html
echo "<h1>My App</h1>" > components/my-app/html/index.html
```

4. Include it in root `docker-compose.yml`:
```yaml
include:
  - tunnel/docker-compose.yml
  - ingress/docker-compose.yml
  - components/test/docker-compose.yml
  - components/http-test/docker-compose.yml
  - components/my-app/docker-compose.yml  # Add this line
```

5. Start the component:
```bash
docker compose up -d my-app
```

Traefik will auto-discover it via labels and route `https://my-app.yourdomain.com` to your service. No Traefik restart needed!

### Pre-configured test components

- **test**: NGINX service routed via Traefik at `https://test.yourdomain.com` (internal network only)
- **http-test**: NGINX server bound to `http://localhost:80` for local connectivity testing

## 4) Test That Everything Works Fine

### Local connectivity tests
```bash
# Test local HTTP server on port 80
curl -I http://localhost:80
curl http://localhost:80

# Test Traefik dashboard locally
curl -I http://localhost:8080
```

Expected: Local HTTP test returns 200 with "NGINX HTTP Server OK".

### Tunnel & Traefik tests
```bash
# Check tunnel status
docker compose logs tunnel --tail=20

# Check Traefik logs
docker compose logs ingress --tail=20

# Validate merged config
docker compose config
```

### Public routing tests (after Cloudflare setup)
```bash
# Test via HTTPS (will redirect to Cloudflare Access if enabled)
curl -I https://test.yourdomain.com
curl -I https://traefik.yourdomain.com

# After authenticating via browser, these should return 200
```

Expected behavior:
- Accessing `https://<your-domain>/` protected routes should redirect to Cloudflare Access login (302)
- After successful authentication, routed services should return 200
- Adding a new component and starting it should make it routable immediately without restarting Traefik

## Security Notes

- Cloudflare Access protects all public hostnames - only allow trusted users
- Traefik dashboard is behind basic auth and also recommended to be protected by Cloudflare Access
- Docker socket is mounted read-only (`:ro`) to Traefik for safety
- Traefik dashboard is only published to `127.0.0.1:8080` (not exposed to network)
- No component services publish ports to host by default; only `http-test` publishes `127.0.0.1:80:80` for local testing
- Keep `.env` and credentials files secure - never commit them to git

## Troubleshooting

| Issue | Solution |
|---|---|
| `network AICD-net not found` | Run `./network/create-network.sh` or `docker network create AICD-net` |
| Tunnel not connecting | Check `CF_TUNNEL_TOKEN` and `creds.json` are correct; check `docker compose logs tunnel` |
| 404 when accessing subdomain | Verify DNS is proxied (orange cloud) in Cloudflare and tunnel public hostname is configured |
| Traefik not routing | Check container has correct labels and is on `AICD-net`; verify with `docker compose logs ingress` |
| Cloudflare Access loop | Ensure your email is in the Access policy allowlist |
| Port 80 conflict | Stop any local service using port 80 before starting `http-test` |

## Validation Checklist

- [ ] `.env` configured with correct values
- [ ] Docker network `AICD-net` exists
- [ ] `cloudflared` connects successfully (tunnel healthy)
- [ ] Traefik starts without errors
- [ ] Traefik dashboard accessible locally and via tunnel
- [ ] Test component routable at `https://test.yourdomain.com` after auth
- [ ] Local HTTP test works at `http://localhost:80`
- [ ] Adding new component auto-registers with Traefik
- [ ] `docker compose config` validates successfully
