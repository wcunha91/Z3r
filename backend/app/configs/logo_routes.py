# app/configs/logo_routes.py
# ---------------------------------------------------------------
# Rotas para gerenciamento de logos por hostgroup (upload, get, delete).
# Os logos são armazenados em configs/logos/ com o nome logohostgroup{id}.{ext}
# Suporta PNG, JPG, JPEG, SVG, WEBP com tamanho máximo de 2MB.
# ---------------------------------------------------------------

from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from pathlib import Path
from PIL import Image
import shutil
from datetime import datetime
from app.core.logging import logger

router = APIRouter()

# Diretório onde os logos serão armazenados
LOGO_DIR = Path("configs/logos")
LOGO_DIR.mkdir(parents=True, exist_ok=True)

# Configurações
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "svg", "webp"}
MAX_FILE_SIZE_MB = 2


def get_logo_path(hostgroup_id: str, extension: str):
    return LOGO_DIR / f"logohostgroup{hostgroup_id}.{extension}"

@router.get("/logo")
def list_logos():
    """
    Lista todos os arquivos de logo disponíveis com data de criação.
    """
    try:
        logos = []
        for f in LOGO_DIR.glob("*.*"):
            if f.suffix[1:].lower() in ALLOWED_EXTENSIONS:
                created_time = datetime.fromtimestamp(f.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                logos.append({
                    "filename": f.name,
                    "created_at": created_time
                })
        logger.info(f"Listagem de logos encontrados: {logos}")
        return logos
    except Exception as e:
        logger.error(f"Erro ao listar logos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar logos: {str(e)}")
    
@router.post("/logo/{hostgroup_id}")
def upload_logo(hostgroup_id: str, file: UploadFile = File(...)):
    """
    Faz upload de um logo para o hostgroup especificado.
    Substitui o logo existente se já houver.
    """
    try:
        # Valida extensão
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Extensão '{ext}' não permitida. Use: {', '.join(ALLOWED_EXTENSIONS)}")

        # Valida tamanho (stream para evitar carregar tudo na memória)
        file.file.seek(0, 2)  # move para o fim do arquivo
        size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(status_code=400, detail=f"Arquivo muito grande ({size_mb:.2f}MB). Máximo permitido: {MAX_FILE_SIZE_MB}MB")

        # Valida imagem com Pillow (exceto SVG)
        if ext != "svg":
            try:
                img = Image.open(file.file)
                img.verify()
                file.file.seek(0)
            except Exception:
                raise HTTPException(status_code=400, detail="Arquivo não é uma imagem válida")

        # Salva o arquivo
        logo_path = get_logo_path(hostgroup_id, ext)
        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Logo salvo: {logo_path}")
        return {"status": "success", "filename": logo_path.name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer upload do logo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")


@router.get("/logo/{filename}")
def get_logo(filename: str):
    """
    Retorna o logo solicitado.
    """
    safe_filename = Path(filename).name  # proteção contra path traversal
    file_path = LOGO_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Logo não encontrado")
    try:
        return Response(content=file_path.read_bytes(), media_type=f"image/{file_path.suffix[1:]}")
    except Exception as e:
        logger.error(f"Erro ao carregar logo: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao carregar logo")


@router.delete("/logo/{filename}")
def delete_logo(filename: str):
    """
    Exclui o logo especificado.
    """
    safe_filename = Path(filename).name  # proteção contra path traversal
    file_path = LOGO_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Logo não encontrado")
    try:
        file_path.unlink()
        logger.info(f"Logo excluído: {safe_filename}")
        return {"status": "deleted", "filename": safe_filename}
    except Exception as e:
        logger.error(f"Erro ao excluir logo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir logo: {str(e)}")


# Utilitário para uso no ReportService
def get_logo_for_hostgroup(hostgroup_id: str) -> Path:
    """
    Retorna o caminho do logo para o hostgroup especificado, ou None se não existir.
    """
    for ext in ALLOWED_EXTENSIONS:
        candidate = get_logo_path(hostgroup_id, ext)
        if candidate.exists():
            logger.info(f"Logo personalizado encontrado: {candidate}")
            return candidate
    logger.info("Logo personalizado não encontrado, usando padrão")
    return Path("app/static/logo.png")
