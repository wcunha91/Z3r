# Deploy com Traefik (Backend apenas)

## 1) Pré-requisitos
- Domínio apontando para o IP do servidor: `app.z3report.com`
- Docker e Docker Compose instalados
- Porta 80/443 livres no host

## 2) Estrutura
backend/
app/
storage/
Dockerfile
docker-compose.yml
.env
docker/traefik/
acme.json
dynamic.yml


## 3) Preparação
```bash
cd backend
cp .env.production.example .env
# edite .env e preencha segredos

mkdir -p docker/traefik storage
touch docker/traefik/acme.json
chmod 600 docker/traefik/acme.json
- Traefik criará e renovará automaticamente o certificado Let's Encrypt em acme.json.

4) Subir os serviços
make build
make up

5) Testes rápidos

curl -I https://app.z3report.com/api/ → 200/401/403 (conforme auth/guard)

docker compose logs traefik -f → verifique obtenção do certificado (ACME)

6) Logs e manutenção

make logs / make logs-api / make logs-traefik

Renovações de certificado são automáticas (ACME HTTP-01).

7) Hardening/Boas práticas

Mantenha ENV=production e ROOT_PATH=/api.

Desabilite CORS no backend em produção (Traefik expõe o serviço).

Confirme que seu require_internal_proxy aceita X-Internal-Proxy: 1.

Não exponha porta 8000 no host, apenas Traefik deve publicar.

Se quiser ocultar /api/docs em prod, inicie o FastAPI com docs_url=None.


---

## Ajustes mínimos no `app/main.py` (recomendado)

1) **CORS somente em DEV**:
```python
from fastapi.middleware.cors import CORSMiddleware
import os

if os.getenv("ENV") != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

Proxy Guard: seu Traefik já envia X-Internal-Proxy: 1. Se preferir um segredo, troque para X-Proxy-Secret: <valor> e:

adicione PROXY_SECRET no .env;

altere a label:
traefik.http.middlewares.api-headers.headers.customrequestheaders.X-Proxy-Secret=<valor>.

