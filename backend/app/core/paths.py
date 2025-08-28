# app/core/paths.py
# --------------------------------------------------------------------
# Centraliza diretórios de dados em produção/DEV usando STORAGE_DIR.
# Por padrão, usamos /app/storage (montado via volume no docker-compose).
# Mantém tudo organizado: logs, reports, configs e tmp.
# --------------------------------------------------------------------
from pathlib import Path
import os

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_storage_dir() -> Path:
    """
    Lê STORAGE_DIR do ambiente. Se não existir, usa /app/storage.
    Cria a pasta, se necessário, e retorna o Path absoluto.
    """
    base = os.getenv("STORAGE_DIR", "/app/storage")
    base_path = Path(base).resolve()
    return _ensure_dir(base_path)

# Pastas padronizadas de dados
STORAGE_DIR = get_storage_dir()
LOGS_DIR    = _ensure_dir(STORAGE_DIR / "logs")
REPORTS_DIR = _ensure_dir(STORAGE_DIR / "reports")
CONFIG_DIR  = _ensure_dir(STORAGE_DIR / "configs")
TMP_DIR     = _ensure_dir(STORAGE_DIR / "tmp")
