# AI Cloud Data (AICD) platform

A collection of tools running locally on Docker Desktop on your machine; It will hosts all needed tools to deploy, manage and run your AI Applications;

Table Of Content
 * [Services](#services)
 * [Configuration](#configuration)
 * [Usage](#usage)
 * [Testing (macOS CLI)](#testing)


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

<a id="configuration"></a>
## Configuration

clone this repository locally
```
git clone https://github.com/heibalvin/AICD.git
```

copy `sample.env` into `.env`. update the environment variables
```
# POSTGRES
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<YOUR_POSTGRES_PASSWORD>
POSTGRES_DB=default
POSTGRES_URI=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}
```

start the services
```
docker compose up -d
```

<a id="ollama"></a>
## Ollama

TBD

<a id="traefik"></a>
## Traefik

TBD

<a id="postgres"></a>
## Postgres

TBD

<a id="nginx"></a>
## Nginx

TBD

<a id="testing"></a>
## Testing (macOS CLI)

Run the following checks from your Mac terminal to verify each service is reachable.

Prerequisites: services must be running (`docker compose up -d`) and `.env` populated.

### Traefik ingress (ports 80/11434/5432)

Traefik routes port 80 to Nginx, 11434 to Ollama, and 5432 to Postgres.

```bash
# Nginx via Traefik port 80
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:80

# Ollama via Traefik port 11434
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:11434

# Traefik dashboard
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080
```

### Ollama

```bash
# List pulled models (expects llama3.2:3b)
curl -s http://localhost:11434/api/tags | jq .

# Generate a completion
curl -s http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "hello",
  "stream": false
}' | jq .
```

### Nginx

```bash
# Direct to Nginx container port 80
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:80
```

### Postgres

```bash
# Connect via the aicd database
psql "postgresql://aicd:<YOUR_POSTGRES_PASSWORD>@localhost:5432/aicd" -c "SELECT 1;"

# List databases
psql "postgresql://aicd:<YOUR_POSTGRES_PASSWORD>@localhost:5432/aicd" -c "\l"
```

### Full stack status

```bash
docker compose ps
```
