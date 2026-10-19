# AICD - AI Cloud Data Platform

Local Docker-Desktop based dev platform routed via Cloudflare Tunnel with Traefik dynamic ingress and Cloudflare Access authentication.

## Overview

- **Ingress**: Traefik v3.5.3 (auto-discovers containers via Docker labels)
- **Tunnel**: Cloudflare Zero Trust Tunnel (cloudflared 2025.10.0) routes `dev.akashatek.com` to Traefik on Docker Desktop
- **Auth**: Cloudflare Access (Zero Trust) protects `dev.akashatek.com` and all `*.dev.akashatek.com` routes
- **Network**: All containers on `AICD-net` Docker network
- **TLS**: Handled at Cloudflare edge; internal traffic is HTTP
- **Images pinned**: traefik:v3.5.3, cloudflare/cloudflared:2025.10.0, nginx:1.29.2-alpine
- **Public site**: `akashatek.com` and `blog.akashatek.com` can remain on Google DNS (or be redirected as needed)

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose v2.20+
- Domain `akashatek.com` (currently managed by Google Domains/Google Cloud DNS - nameservers ns-cloud-*.googledomains.com)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/) access

## 1) Cloudflare Setup with Google-Managed Domain (Subdomain-Only)

Since `akashatek.com` is managed by Google (not Cloudflare NS), you do **not** need to move nameservers. You can route only `dev.akashatek.com` through Cloudflare Tunnel by adding a CNAME in Google DNS pointing to Cloudflare.

### Option A: Subdomain-only (recommended, no NS change)

This keeps `akashatek.com` and `blog.akashatek.com` on Google while sending `dev.akashatek.com` traffic through Cloudflare for Tunnel + Zero Trust Access.

#### Step 1: Create Zero Trust Tunnel
1. Go to [Cloudflare Zero Trust > Networks > Tunnels](https://one.dash.cloudflare.com/?to=/:account/networks/tunnels)
2. Create tunnel > Cloudflared
3. Name: `aicd-dev`
4. Save and copy **Tunnel Token** (`CF_TUNNEL_TOKEN`) and **Tunnel ID** (`CF_TUNNEL_ID`)

#### Step 2: Configure public hostname for the tunnel
1. In the tunnel > **Public Hostname** > Add
2. Subdomain: `dev`
3. Domain: choose a domain you control in your Cloudflare account. If `akashatek.com` isn't in Cloudflare zone, add it as a **zone** in Cloudflare (you can add it without changing nameservers first - "CNAME setup" is possible). Alternatively, create the public hostname under a zone you manage, then point the Google DNS CNAME to the Cloudflare tunnel target.
4. Service Type: `HTTP`, URL: `traefik:80`
5. Save. Cloudflare will show the CNAME target (typically `<tunnel-id>.cfargotunnel.com` or the specific hostname target for this tunnel)

#### Step 3: Add CNAME in Google DNS
1. Go to [Google Domains > DNS](https://domains.google.com/) (or Google Cloud DNS for your domain)
2. Add a DNS record:
   - **Type**: `CNAME`
   - **Host/name**: `dev`
   - **Value/target**: `<your-tunnel-id>.cfargotunnel.com` (or the exact target shown in Cloudflare Tunnel public hostname)
   - **TTL**: default/auto
3. Save. Do **not** proxy via Google (CNAME to Cloudflare tunnel target)

This routes `dev.akashatek.com` through Cloudflare's edge to your tunnel.

#### Step 4: (Optional) Redirect akashatek.com/blog.akashatek.com
If you want redirects while keeping Google DNS:
1. Keep A/AAAA/CNAME as-is in Google for root/blog
2. For HTTP redirects, use your hosting (InfinityFree) or a Cloudflare Worker/Rules only if zone is fully on Cloudflare. With Google-managed DNS, easiest is configure redirects at InfinityFree or on your origin. If you still want Cloudflare Rules, you need full NS delegation.

#### Step 5: Cloudflare Access
1. [Zero Trust > Access > Applications](https://one.dash.cloudflare.com/?to=/:account/access/apps) > Add Self-hosted
2. Name: `AICD Dev Platform`
3. Public hostnames: `dev.akashatek.com`, `*.dev.akashatek.com`
4. Add allow policy for your users
5. Save

> Traffic hits Cloudflare because the CNAME points to cfargotunnel.com, so Access/Zero Trust works without moving NS.

### Option B: Full delegation (move NS to Cloudflare)
1. Add `akashatek.com` to Cloudflare, follow onboarding (it may detect records)
2. Change nameservers at Google Domains to Cloudflare's NS
3. Then you can use Redirect Rules for root/blog and full control. This also works fine.

## 2) Start Tunnel & Traefik

### Step 1: Environment
```bash
cd /Users/heibalvin/Github/heibalvin/AICD
cp sample.env .env
```

`.env`:
```bash
DOMAIN=dev.akashatek.com
CF_TUNNEL_ID=your-tunnel-id
CF_TUNNEL_TOKEN=your-tunnel-token
TRAEFIK_DASHBOARD_USER=admin
TRAEFIK_DASHBOARD_PASS=your-secure-password
```

### Step 2: Auth
Uses `CF_TUNNEL_TOKEN`. `tunnel/docker-compose.yml` also mounts `~/.cloudflared/creds.json:ro` (optional if token present).

### Step 3: Network + Start
```bash
./network/create-network.sh
docker compose up -d
docker compose ps
docker compose logs -f tunnel
docker compose logs -f ingress
```

### Step 4: Dashboard
- Local: http://localhost:8080
- Tunnel: https://traefik.dev.akashatek.com (behind Access)

## 3) Add NGINX Component & Routing Rules

Same as before; routes are `*.dev.akashatek.com` via Traefik labels.

Example component with pinned image:
```yaml
image: nginx:1.29.2-alpine
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.myapp.rule=Host(`myapp.dev.akashatek.com`)"
  - "traefik.http.routers.myapp.entrypoints=web"
  - "traefik.http.services.myapp.loadbalancer.server.port=80"
```

Include in root `docker-compose.yml`, `docker compose up -d <name>`.

## 4) Test

```bash
# Local
curl -I http://localhost:80
curl http://localhost:8080

# DNS (verify CNAME)
dig dev.akashatek.com CNAME +short

# Public
curl -I https://dev.akashatek.com
curl -I https://traefik.dev.akashatek.com
curl -I https://test.dev.akashatek.com
```

With Google DNS + CNAME to cfargotunnel.com, `dev.akashatek.com` resolves to Cloudflare tunnel target and routes through Access/Tunnel. Root/blog remain as configured in Google.

## Troubleshooting

| Issue | Solution |
|---|---|
| `dev.akashatek.com` doesn't resolve | Check CNAME in Google DNS points to `<tunnel-id>.cfargotunnel.com`; allow propagation (TTL) |
| Tunnel fails | Verify Tunnel ID/Token; `docker compose logs tunnel` |
| 404s | Public hostname `dev.akashatek.com` (and `*.dev.akashatek.com` if needed) configured in tunnel to `http://traefik:80` |
| Access loop | User in Access allow policy |
| Port 80 conflict | Free :80 or stop `http-test` |

## Squarespace DNS Setup

If `akashatek.com` is connected to Squarespace (Squarespace Domains or connected domain), follow these steps.

### A) Route akashatek.com and blog.akashatek.com to https://akashatek.infinityfreeapp.com/

Squarespace doesn't support raw "forwarding URL" in the same way as Cloudflare Page Rules for apex+subdomain in some cases. Recommended approaches:

**Option 1: Use Squarespace Redirects (if using Squarespace as site host)**
1. Go to [Squarespace > Settings > Advanced > URL Mappings](https://support.squarespace.com/hc/en-us/articles/205815308-URL-Mappings)
2. Add mappings to 301 redirect:
   - `/` -> `https://akashatek.infinityfreeapp.com/` (301)
   - But for apex domain vs www/blog, better to handle at DNS level with external redirects

**Option 2: Use DNS + external redirect service (recommended for external target)**
Since you're sending traffic to an external InfinityFree URL:
1. In Squarespace Domains > [DNS Settings](https://support.squarespace.com/hc/en-us/articles/360002101888-Adding-DNS-records-to-your-Squarespace-managed-domain), point traffic appropriately. For full redirect to external host, easiest is to use a redirect at the hosting level or Cloudflare (if delegated). If Squarespace DNS is authoritative:
   - For `blog.akashatek.com`: add a `CNAME` record `blog` -> `akashatek.infinityfreeapp.com` (if InfinityFree accepts CNAME for the target). Some hosts require A records; check InfinityFree docs.
   - For apex `akashatek.com`: CNAME not allowed at apex on many DNS providers - use `A` records if InfinityFree provides IPs, or use ALIAS/ANAME if available. Squarespace DNS may not offer ALIAS; alternatively use 301 redirect via Squarespace if hosting a placeholder page, or delegate to Cloudflare and use Redirect Rules.

**Option 3: Delegate DNS to Cloudflare (cleanest for redirects)**
1. In Squarespace Domains, get nameservers [Manage domain > Nameservers](https://support.squarespace.com/hc/en-us/articles/212220808-Changing-your-domain-s-nameservers)
2. Change to Cloudflare nameservers (add zone in Cloudflare, copy NS)
3. In Cloudflare, add Redirect Rules for apex and `blog` to InfinityFree (as above). This gives clean 301 redirects preserving query strings.

### B) Route dev.akashatek.com to Cloudflare Tunnel (Squarespace DNS)

With Squarespace DNS authoritative (no NS change):
1. Go to Squarespace > Domains > DNS Settings for `akashatek.com`
2. Add a `CNAME` record:
   - **Name/Host**: `dev`
   - **Type**: `CNAME`
   - **Data/Target**: `<tunnel-id>.cfargotunnel.com` (from Cloudflare Tunnel Public Hostname)
   - **TTL**: default
3. Save. Do not enable any proxying in Squarespace (it's just DNS). Cloudflare will handle edge/Tunnel/Access.
4. In Cloudflare Zero Trust Tunnel, ensure Public Hostname `dev.akashatek.com` is configured pointing to `http://traefik:80` and Access policy covers `dev.akashatek.com` and `*.dev.akashatek.com`.

> If Squarespace shows "CNAME flattening" or doesn't allow CNAME for subdomain in some cases, use the same target. Alternatively delegate only dev by not possible; easier to delegate zone to Cloudflare for full flexibility, or use CNAME as above.
