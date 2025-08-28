# app/configs/routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, ValidationError
from pathlib import Path
from datetime import datetime
import json
from app.core.logging import logger
from typing import List, Optional, Dict, Any
import re

router = APIRouter()

CONFIG_DIR = Path("configs/")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

class ConfigPayload(BaseModel):
    hostgroup: Dict[str, Any]
    hosts: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None
    emails: Optional[List[EmailStr]] = []
    frequency: Optional[str] = None
    logo_filename: Optional[str] = None
    analyst: Optional[str] = None
    comments: Optional[str] = None
    last_generated: Optional[str] = None

    class Config:
        extra = "allow"

def sanitize_filename(name: str) -> str:
    """Remove espaços, barras e caracteres especiais do nome do hostgroup para uso em arquivos."""
    # Somente letras, números, _ e -
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip()).lower()

@router.post("/configs/")
def save_config(payload: dict):
    """
    Salva uma nova configuração recebida no payload como arquivo JSON.
    Exige os campos obrigatórios hostgroup e hosts.
    """
    try:
        validated = ConfigPayload(**payload)
    except ValidationError as e:
        logger.error(f"Validação falhou ao salvar configuração: {e}")
        raise HTTPException(status_code=400, detail=f"Erro de validação: {e.errors()}")

    hostgroup_name = validated.hostgroup.get("name", "hostgroup")
    sanitized_hostgroup = sanitize_filename(hostgroup_name)
    filename = f"{sanitized_hostgroup}_config_{datetime.now().strftime('%Y-%m-%d')}.json"
    file_path = CONFIG_DIR / filename
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(validated.dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Configuração salva: {filename}")
        return {"status": "success", "filename": filename}
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")

@router.get("/configs/")
def list_configs():
    """
    Lista todos os arquivos de configuração na pasta configs/.
    """
    try:
        files = sorted([f.name for f in CONFIG_DIR.glob("*.json")], reverse=True)
        return files
    except Exception as e:
        logger.error(f"Erro ao listar configurações: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar: {str(e)}")

@router.get("/configs/{filename}")
def load_config(filename: str):
    """
    Retorna o conteúdo do JSON da configuração solicitada.
    """
    file_path = CONFIG_DIR / Path(filename).name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Configuração carregada: {filename}")
        return data
    except Exception as e:
        logger.error(f"Erro ao carregar configuração: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao carregar: {str(e)}")

@router.delete("/configs/{filename}")
def delete_config(filename: str):
    """
    Exclui o arquivo de configuração informado.
    """
    safe_filename = Path(filename).name
    file_path = CONFIG_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    try:
        file_path.unlink()
        logger.info(f"Configuração excluída: {safe_filename}")
        return {"status": "deleted", "filename": safe_filename}
    except Exception as e:
        logger.error(f"Erro ao excluir configuração: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir: {str(e)}")

@router.put("/configs/{filename}")
def update_config(filename: str, payload: dict):
    """
    Atualiza o arquivo de configuração com novos dados.
    """
    safe_filename = Path(filename).name
    file_path = CONFIG_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    try:
        validated = ConfigPayload(**payload)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(validated.dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Configuração atualizada: {safe_filename}")
        return {"status": "updated", "filename": safe_filename}
    except ValidationError as e:
        logger.error(f"Validação falhou ao atualizar configuração: {e}")
        raise HTTPException(status_code=400, detail=f"Erro de validação: {e.errors()}")
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar: {str(e)}")
