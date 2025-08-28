# Makefile - atalhos de build/deploy/logs

SHELL := /bin/bash

build:
\tdocker compose build

up:
\tdocker compose up -d

down:
\tdocker compose down

restart:
\tdocker compose down && docker compose up -d

logs:
\tdocker compose logs -f --tail=200

logs-api:
\tdocker compose logs -f api

logs-traefik:
\tdocker compose logs -f traefik

ps:
\tdocker compose ps

permissions:
\tchmod 600 docker/traefik/acme.json || true
