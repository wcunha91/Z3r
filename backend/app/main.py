# app/main.py
from fastapi import FastAPI, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
import os

# Carrega variáveis de ambiente (útil em DEV; em PROD o Docker injeta pelo env_file)
load_dotenv(override=True)

# Rotas/recursos
from app.zabbix.routes import router as zabbix_router
from app.reports.routes import router as reports_router
from app.configs.routes import router as configs_router
from app.configs.logo_routes import router as logos_router
from app.auth.routes import router as auth_router
from app.glpi import routes as glpi_routes

# Infra
from app.core.logging import logger
from app.scheduler import start_scheduler

# Proteções
from app.auth.security import get_current_user
from app.auth.proxy_guard import require_internal_proxy

# -----------------------------------------------------------------------------
# Ambiente / Root Path / OpenAPI
# -----------------------------------------------------------------------------
ENV = os.getenv("ENV", "development").lower()
ROOT_PATH = os.getenv("ROOT_PATH", "")  # Em produção, via Traefik, usamos /api
OPENAPI_ENABLED = os.getenv("OPENAPI_ENABLED", "false").lower() in {"1", "true", "yes"}

# Em produção, por padrão ocultamos a documentação;
# se quiser expor (sempre atrás do proxy), defina OPENAPI_ENABLED=true.
docs_url = "/docs" if (ENV != "production" or OPENAPI_ENABLED) else None
redoc_url = "/redoc" if (ENV != "production" or OPENAPI_ENABLED) else None
openapi_url = "/openapi.json" if (ENV != "production" or OPENAPI_ENABLED) else None

app = FastAPI(
    title="Athena Reports",
    root_path=ROOT_PATH,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
# Em DEV liberamos localhost; em PROD só aplica CORS se CORS_ALLOW_ORIGINS existir.
DEV_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
ALLOW_ORIGIN_REGEX = r"http://localhost:\d+"

if ENV != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ALLOWED_ORIGINS,
        allow_origin_regex=ALLOW_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
else:
    cors_from_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if cors_from_env:
        allowed = [o.strip() for o in cors_from_env.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["Content-Disposition"],
        )
        logger.info(f"[CORS] Aplicado em produção para: {allowed}")
    else:
        logger.info("[CORS] Desabilitado em produção (Traefik publica o serviço).")

# -----------------------------------------------------------------------------
# Arquivos estáticos (servidos em /static; com ROOT_PATH, ficam em /api/static)
# -----------------------------------------------------------------------------
STATIC_FILES_PATH = os.getenv("STATIC_FILES_PATH", "app/static")
os.makedirs(STATIC_FILES_PATH, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_FILES_PATH), name="static")

# -----------------------------------------------------------------------------
# Dependências globais
# -----------------------------------------------------------------------------
# common_deps: Exige PASSAGEM PELO PROXY + JWT válido (para quase tudo)
common_deps = [Depends(require_internal_proxy), Depends(get_current_user)]
# proxy_only: Exige apenas PASSAGEM PELO PROXY (ex.: /auth/login acessível)
proxy_only = [Depends(require_internal_proxy)]

# -----------------------------------------------------------------------------
# Rotas
# -----------------------------------------------------------------------------
@app.get("/", dependencies=common_deps)
def root():
    logger.info("Acesso à rota raiz '/'")
    return {"message": "Athena Reports ativo", "env": ENV}

# Healthcheck: exige apenas passar pelo proxy (Traefik adiciona o header)
@app.get("/healthz", dependencies=[Depends(require_internal_proxy)])
def healthz():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}

# Inclui routers da app (protegidos por proxy + JWT)
app.include_router(zabbix_router, dependencies=common_deps)
app.include_router(reports_router, dependencies=common_deps)
app.include_router(configs_router, dependencies=common_deps)
app.include_router(logos_router, dependencies=common_deps)
app.include_router(glpi_routes.router, dependencies=common_deps)

# Router de autenticação: exige proxy em todo o router.
# Dentro dele:
#  - /auth/login NÃO exige get_current_user (permite logar)
#  - /auth/me já exige get_current_user no próprio handler
app.include_router(auth_router, dependencies=proxy_only)

# -----------------------------------------------------------------------------
# (DEV) Catch-all OPTIONS para preflight fora do CORSMiddleware
# -----------------------------------------------------------------------------
if ENV != "production":
    @app.options("/{full_path:path}")
    def options_catch_all(full_path: str):
        # Sem corpo, apenas status vazio para satisfazer eventuais preflights
        return Response(status_code=204)

# -----------------------------------------------------------------------------
# Scheduler
# -----------------------------------------------------------------------------
# Em produção, o recomendado é rodar o scheduler em um container separado.
# Mesmo assim, deixamos a opção de habilitar via env para ambientes simples.
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() in {"1", "true", "yes"}

@app.on_event("startup")
def startup_event():
    if ENABLE_SCHEDULER:
        app.state.scheduler = start_scheduler()
        logger.info("[SCHEDULER] Iniciado no processo da API (ENABLE_SCHEDULER=true)")
    else:
        logger.info("[SCHEDULER] Desativado no processo da API (use o container 'scheduler').")
