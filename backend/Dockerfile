# Dockerfile (backend produção, compacto e seguro)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    TZ=America/Sao_Paulo

# Dependências nativas mínimas (ajuste se usar ReportLab/cairo/etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências primeiro para otimizar cache
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o código
COPY . .

# Usuário não-root
RUN useradd -m appuser && chown -R appuser:appuser /app
RUN useradd -m -u 1000 -U appuser && chown -R appuser:appuser /app

# Copia o entrypoint e dá permissão de execução
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

# Rode como root no ENTRYPOINT (para chown) e depois o script troca para appuser
USER root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# O CMD é passado para o entrypoint e será executado como appuser
CMD ["gunicorn", "app.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
