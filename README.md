# AI Cloud Data (AICD) platform

A collection of tools running locally on Docker Desktop on your machine; It will hosts all needed tools to deploy, manage and run your AI Applications;

Lineup:
 - ollama/ollama:0.34.4
 - postgres:18.6
 - traefik:3.7.15
 - nginx:1.31.7-alpine

## Install

clone this repository locally
```
git clone https://github.com/heibalvin/AICD.git
```

copy `sample.env` into `.env`. update the environment variables
```
# POSTGRES
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<YOUR-POSTGRES-PASSWORD>
POSTGRES_DB=default
POSTGRES_URI=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}
```

start the services
```
docker compose up -d
```
