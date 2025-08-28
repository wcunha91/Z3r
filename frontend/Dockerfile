# --- Stage 1: build ---
FROM node:20-alpine AS build
WORKDIR /app

# Instala dependências
COPY package*.json ./
RUN npm ci

# Copia código e builda (ajuste o comando se não for Vite/React)
COPY . .
# Opcional: injeta variável de build (se você usa import.meta.env.VITE_API_BASE_URL)
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# --- Stage 2: serve estático ---
FROM nginx:1.27-alpine

# Nginx config otimizada para SPA (cache de assets com hash, fallback no index.html)
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Conteúdo estático
COPY --from=build /app/dist /usr/share/nginx/html

# (Opcional) Injeção de variáveis em runtime via env.js
# Os scripts em /docker-entrypoint.d/*.sh rodam antes do nginx start
COPY docker/50-env-inject.sh /docker-entrypoint.d/50-env-inject.sh
RUN chmod +x /docker-entrypoint.d/50-env-inject.sh

EXPOSE 80
