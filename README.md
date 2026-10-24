# AI Cloud Data (AICD) platform

A collection of tools running locally on Docker Desktop on your machine; It will hosts all needed tools to deploy, manage and run your AI Applications;

Table Of Content
 * [Services](#services)
 * [Install](#install)
 * [Local Domain](#local-domain)

Components
 * [Ollama](#ollama)
 * [Traefik](#traefik)
 * [Postgres](#postgres)
 * [Nginx](#nginx)

<a id="services"></a>
## Services

| Services  | Description  |
|---|---|
| ![ollama logo](./Assets/logo-ollama.png)  | [Ollama](#ollama) is the engine that brings large language models (LLMs) to your desktop. It allows you to download, run, and manage open-source models like Llama 3 directly on your local machine, eliminating the need for expensive cloud services. Ollama simplifies the entire process, making it easy to experiment with different models for your AI applications.  |
| ![traefik logo](./Assets/logo-traefik.png)  | [Traefik](#traefik) ingress controller is a modern, cloud-native reverse proxy and load balancer that manages external HTTP/HTTPS access to services inside a Kubernetes cluster. It reads standard Kubernetes Ingress resources or custom IngressRoute definitions and dynamically maps traffic to your containerized  |
| ![postgres logo](./Assets/logo-postgres.png)  | [Postgres](#postgres) is a powerful, open-source relational database. While it's known for its reliability and robustness in storing traditional, structured data, it also plays a critical role in modern AI stacks. In this context, Postgres is used to manage the metadata and structured information associated with your AI application, providing a solid foundation for user data, logs, and other critical backend needs.  |
| ![nginx logo](./Assets/logo-nginx.png)  | [Nginx](#nginx)  is a high-performance, open-source HTTP web server, reverse proxy, content cache, and load balancer. Created by Igor Sysoev and released in 2004, it is currently one of the most widely used web servers in the world. |

Lineup:
 - ollama/ollama:0.34.4
 - postgres:18.6
 - traefik:3.7.15
 - nginx:1.31.7-alpine

<a id="install"></a>
## Install

clone this repository locally
```
git clone https://github.com/heibalvin/AICD.git
```

copy `sample.env` into `.env`. update the environment variables
```
# POSTGRES
POSTGRES_HOST=aicd_postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<YOUR_POSTGRES_PASSWORD>
POSTGRES_DB=default
POSTGRES_URI=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}

# POSTGRES AICD
POSTGRES_AICD_USER=aicd
POSTGRES_AICD_PASSWORD=<YOUR_AICD_PASSWORD>
POSTGRES_AICD_DB=aicd

# OLLAMA
OLLAMA_HOST=aicd_ollama

# DOMAIN
DOMAIN=local.akashatek.com
```

start the services
```
docker compose up -d
```

<a id="domain"></a>
## Local Domain

The whole deployment is served under `local.akashatek.com`. Before changing Cloudflare
or SquareSpace DNS, test locally by mapping the domain to your machine:

### 1. Add to `/etc/hosts`

```
sudo sh -c 'echo "127.0.0.1 local.akashatek.com" >> /etc/hosts'
```

This only affects your machine and does not touch `www.akashatek.com`, MX, or
Google Workspace records at SquareSpace.

### 2. Start

```
docker compose up -d
```

### Routing under `local.akashatek.com`

| Path | Service |
|------|---------|
| `local.akashatek.com/` | Nginx (web) |
| `local.akashatek.com/ollama/` | Ollama |
| `local.akashatek.com/postgres/` | Postgres (TCP, 5432) |

Cloudflare Tunnel and SquareSpace DNS can be added later to expose
`local.akashatek.com` externally. Until then, `/etc/hosts` keeps traffic local.


<a id="ollama"></a>
## Ollama

```bash
# Generate a completion
curl -s http://local.akashatek.com/ollama/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "hello",
  "stream": false
}' | jq .
```

<a id="traefik"></a>
## Traefik

Traefik routes port 80 to Nginx, 11434 to Ollama, and 5432 to Postgres under `local.akashatek.com`.

```bash
# Nginx via Traefik port 80
curl -s -o /dev/null -w "%{http_code}\n" http://local.akashatek.com/

# Ollama via Traefik port 11434
curl -s -o /dev/null -w "%{http_code}\n" http://local.akashatek.com/ollama/

# Traefik dashboard
curl -s -o /dev/null -w "%{http_code}\n" http://local.akashatek.com:8080
```

<a id="postgres"></a>
## Postgres

Postgres is exposed directly on port 5432 (bypasses Traefik, since plain TCP
connections don't carry the SNI Traefik's TCP router requires).

```bash
# From inside the container
docker exec aicd_postgres psql -U aicd -d aicd -c "SELECT 1;"

# List databases
docker exec aicd_postgres psql -U aicd -d aicd -c "\l"
```

<a id="nginx"></a>
## Nginx

```bash
# Direct to Nginx via Traefik
curl -s -o /dev/null -w "%{http_code}\n" http://local.akashatek.com/
```