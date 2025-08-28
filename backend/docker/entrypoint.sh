#!/usr/bin/env sh
set -e

# Configuráveis por env (opcional)
APP_USER="${APP_USER:-appuser}"
STORAGE_DIR="${STORAGE_DIR:-/app/storage}"
CHOWN_ON_START="${CHOWN_STORAGE_ON_START:-true}"   # true/false

# Descobre UID/GID do appuser dentro do container
APP_UID="$(id -u "$APP_USER" 2>/dev/null || echo 1000)"
APP_GID="$(id -g "$APP_USER" 2>/dev/null || echo 1000)"

# Garante estrutura mínima
mkdir -p "$STORAGE_DIR"/{logs,reports,configs,tmp}

# Ajusta perms só se habilitado (default: true)
if [ "$CHOWN_ON_START" = "true" ]; then
  # Faz chown do storage (bind-mount) para o usuário do app
  chown -R "${APP_UID}:${APP_GID}" "$STORAGE_DIR" || true
fi

# Umask mais permissiva p/ grupo (útil em setups com GID compartilhado)
umask 002

# Executa o comando (gunicorn) como appuser
exec su -s /bin/sh -c "$*" "$APP_USER"
