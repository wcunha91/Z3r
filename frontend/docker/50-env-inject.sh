#!/usr/bin/env sh
set -e

# Valores padrão
: "${PUBLIC_PATH:=/}"
: "${API_BASE_URL:=/api}"

# Gera env.js acessível pela SPA (se ela referenciar <script src="/env.js"></script>)
cat > /usr/share/nginx/html/env.js <<EOF
// Gerado em runtime no container
window.__ENV__ = {
  PUBLIC_PATH: "${PUBLIC_PATH}",
  API_BASE_URL: "${API_BASE_URL}"
};
EOF
