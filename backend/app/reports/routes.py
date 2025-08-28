# app/reports/routes.py
"""
Arquivo: app/reports/routes.py
Descrição: Rotas relacionadas à geração, download, visualização, exclusão e envio de relatórios PDF do Athena Reports.
Inclui integração com blocos ITSM/GLPI, controle de agendamento e gerenciador de arquivos de relatório.

Observações importantes:
- Todos os caminhos de arquivos são centralizados via app.core.paths (storage/...), garantindo persistência em Docker.
- Proteções de path traversal via _safe_join_strict.
- Período GLPI é injetado automaticamente conforme a frequência (weekly/monthly).
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Request, Body
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import unquote
from calendar import monthrange
import traceback
import json

from app.reports.service import ReportService
from app.mail.service import send_report_email, send_report_email_sync
from app.core.logging import logger
from app.core.paths import REPORTS_DIR, CONFIG_DIR  # caminhos centralizados

router = APIRouter()

# ======================================================================================
#                                        MODELOS
# ======================================================================================

class GraphInput(BaseModel):
    id: str
    name: str
    from_time: str
    to_time: str

class HostInput(BaseModel):
    id: str
    name: str
    graphs: List[GraphInput]

class HostgroupInput(BaseModel):
    id: str
    name: str

class ReportRequest(BaseModel):
    hostgroup: HostgroupInput
    hosts: List[HostInput]
    summary: Optional[Dict[str, Any]] = None
    logo_filename: Optional[str] = None
    analyst: Optional[str] = None
    comments: Optional[str] = None
    frequency: Optional[str] = None
    summaryOptions: Optional[Dict[str, Any]] = None
    # Blocos opcionais (GLPI/ITSM)
    itsm: Optional[Dict[str, Any]] = None
    glpi: Optional[Dict[str, Any]] = None

class EmailRequest(BaseModel):
    data: ReportRequest
    recipient: Union[EmailStr, List[EmailStr]]

# ======================================================================================
#                                  HELPERS / CONSTANTES
# ======================================================================================

def get_logo_path(logo_filename: Optional[str]) -> Optional[str]:
    """
    Retorna o caminho completo do logo customizado (storage/configs/logos/<arquivo>), caso exista.
    """
    if not logo_filename:
        return None
    logo_path = (CONFIG_DIR / "logos" / logo_filename).resolve()
    try:
        # Segurança: garante que está dentro de CONFIG_DIR/logos
        (logo_path).relative_to((CONFIG_DIR / "logos").resolve())
    except Exception:
        logger.warning(f"[API] Caminho de logo inválido: {logo_path}")
        return None
    if logo_path.exists() and logo_path.is_file():
        return str(logo_path)
    logger.warning(f"[API] Logo informado não encontrado: {logo_path}")
    return None

def _human_size(num_bytes: int) -> str:
    """
    Converte bytes para formato humano (KB/MB/GB).
    """
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} EB"

def _safe_join_strict(base: Path, unsafe_name: str) -> Path:
    """
    Garante que o caminho final esteja DENTRO de 'base', resolvendo symlinks e evitando path traversal.
    Usa 'relative_to' para validação e decodifica nomes URL-encoded.
    """
    safe_name = Path(unquote(unsafe_name)).name  # impede '..' e barras
    final_path = (base / safe_name).resolve()
    base_resolved = base.resolve()
    try:
        final_path.relative_to(base_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho inválido.")
    return final_path

def _first_week_of_month(dt: datetime) -> bool:
    """True se a data estiver entre os 7 primeiros dias do mês."""
    return 1 <= dt.day <= 7

def _month_range(year: int, month: int):
    """Retorna (inicio_date, fim_date) do mês (datetime.date)."""
    last_day = monthrange(year, month)[1]
    inicio = datetime(year, month, 1).date()
    fim = datetime(year, month, last_day).date()
    return inicio, fim

def _prev_month_range(ref: datetime):
    """Retorna (inicio_date, fim_date) do mês anterior ao ref."""
    first_this = ref.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    return _month_range(last_prev.year, last_prev.month)

def _compute_glpi_period(
    frequency: Optional[str],
    start_date: datetime,
    end_date: datetime,
    today: Optional[datetime] = None
):
    """
    Define (inicio_date, fim_date) para GLPI:
      - monthly: mês anterior inteiro
      - weekly:
          * se start_date está na 1ª semana do mês atual -> mês anterior inteiro
          * senão -> a própria semana [start_date, end_date]
      - fallback: usa [start_date, end_date]
    """
    today = today or datetime.now()
    if frequency == "monthly":
        return _prev_month_range(today)
    if frequency == "weekly":
        if _first_week_of_month(start_date):
            return _prev_month_range(today)
        return start_date.date(), end_date.date()
    return start_date.date(), end_date.date()

def _inject_glpi_period(
    cfg: Dict[str, Any],
    start_date: datetime,
    end_date: datetime,
    today: Optional[datetime] = None
):
    """
    Se existir cfg['glpi'] com 'entidade_id', injeta 'inicio'/'fim' automaticamente.
    Nunca apagamos `entidade_id`.
    """
    glpi = cfg.get("glpi")
    if not isinstance(glpi, dict):
        return cfg
    if not glpi.get("entidade_id"):
        return cfg

    frequency = cfg.get("frequency")
    inicio_date, fim_date = _compute_glpi_period(frequency, start_date, end_date, today)
    glpi["inicio"] = inicio_date.isoformat()  # YYYY-MM-DD
    glpi["fim"] = fim_date.isoformat()        # YYYY-MM-DD
    cfg["glpi"] = glpi
    return cfg

def _extract_period_from_report_request_like(data: Union[ReportRequest, Dict[str, Any]]):
    """
    Extrai start_date / end_date a partir do primeiro gráfico do primeiro host.
    Funciona tanto com Pydantic (ReportRequest/HostInput/GraphInput) quanto com dicts.
    """
    try:
        hosts = data.hosts if hasattr(data, "hosts") else data.get("hosts", [])
        if not hosts:
            raise HTTPException(status_code=400, detail="Nenhum host informado.")

        h0 = hosts[0]
        graphs = getattr(h0, "graphs", None) if not isinstance(h0, dict) else h0.get("graphs")
        if not graphs:
            raise HTTPException(status_code=400, detail="Nenhum gráfico informado.")

        g0 = graphs[0]
        from_time = getattr(g0, "from_time", None) if not isinstance(g0, dict) else g0.get("from_time")
        to_time   = getattr(g0, "to_time",   None) if not isinstance(g0, dict) else g0.get("to_time")

        if not from_time or not to_time:
            raise HTTPException(status_code=400, detail="Campos from_time/to_time ausentes no gráfico.")

        start_date = datetime.fromisoformat(str(from_time).replace(" ", "T"))
        end_date   = datetime.fromisoformat(str(to_time).replace(" ", "T"))
        return start_date, end_date

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Falha ao extrair período do payload: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail="Payload inválido para determinar período (from_time/to_time)."
        )

# ======================================================================================
#                                  ENDPOINTS DE RELATÓRIO
# ======================================================================================

@router.post("/reports/pdf")
def generate_pdf_report(data: ReportRequest):
    """
    Gera o relatório PDF (apenas retorna o caminho/filename, sem baixar).
    Injeta período GLPI automaticamente quando aplicável.
    """
    try:
        logger.info("[API] Geração de relatório PDF (manual)")
        start_date, end_date = _extract_period_from_report_request_like(data)
        cfg = json.loads(data.json())
        cfg = _inject_glpi_period(cfg, start_date, end_date)

        file_path = ReportService.generate_pdf_db(ReportRequest(**cfg))
        pdf_file = Path(file_path)
        logger.info(f"[API] Relatório PDF gerado: {file_path}")
        return {"status": "ok", "file_path": file_path, "filename": pdf_file.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Erro ao gerar relatório: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")

@router.post("/reports/pdf/download")
def generate_pdf_download(data: ReportRequest):
    """
    Gera o relatório PDF e retorna para download (Content-Disposition: attachment).
    Injeta período GLPI automaticamente quando aplicável.
    """
    try:
        logger.info("[API] Geração/download de relatório PDF")
        start_date, end_date = _extract_period_from_report_request_like(data)
        cfg = json.loads(data.json())
        cfg = _inject_glpi_period(cfg, start_date, end_date)

        file_path = ReportService.generate_pdf_db(ReportRequest(**cfg))
        pdf_file = Path(file_path)
        if not pdf_file.exists():
            logger.error(f"[API] Arquivo PDF não encontrado após geração: {file_path}")
            raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado após geração")
        return StreamingResponse(
            pdf_file.open("rb"),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_file.name}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Erro ao gerar/baixar relatório: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar e baixar relatório: {str(e)}")

@router.post("/reports/pdf/email")
async def generate_and_email_report(email_req: EmailRequest, background_tasks: BackgroundTasks):
    """
    Gera o relatório PDF e envia por e-mail (suporta múltiplos destinatários).
    Aceita campos 'itsm' e/ou 'glpi' em 'data' para relatórios integrados.
    Injeta período GLPI automaticamente quando aplicável.
    """
    try:
        logger.info(f"[API] Geração/envio de relatório PDF por e-mail para: {email_req.recipient}")
        start_date, end_date = _extract_period_from_report_request_like(email_req.data)
        cfg = json.loads(email_req.data.json())
        cfg = _inject_glpi_period(cfg, start_date, end_date)

        file_path = ReportService.generate_pdf_db(ReportRequest(**cfg))

        recipients = email_req.recipient if isinstance(email_req.recipient, list) else [email_req.recipient]
        periodo = f"{start_date.date()} a {end_date.date()}"
        logo_path = get_logo_path(cfg.get("logo_filename"))

        background_tasks.add_task(
            send_report_email,
            recipients=recipients,
            file_path=file_path,
            hostgroup_name=cfg.get("hostgroup", {}).get("name"),
            periodo=periodo,
            analyst=cfg.get("analyst"),
            comments=cfg.get("comments"),
            logo_path=logo_path
        )
        return {"status": "ok", "message": f"Relatório gerado e enviado para {', '.join(recipients)}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Erro ao gerar/enviar relatório: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar e enviar relatório: {str(e)}")

# ======================================================================================
#                              REPORTS MANAGER (ARQUIVOS)
# ======================================================================================

class ReportFile(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    created_at: str
    modified_at: str
    url_download: str
    url_preview: str

@router.get("/reports/files", response_model=List[ReportFile])
def list_report_files(
    q: Optional[str] = Query(None, description="Filtro por nome do arquivo"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    """
    Lista os PDFs existentes em storage/reports, com filtros opcionais:
      - q: termo no nome do arquivo
      - start_date / end_date: intervalo por data de modificação do arquivo
    """
    try:
        files: List[ReportFile] = []
        for f in REPORTS_DIR.glob("*.pdf"):
            try:
                stat = f.stat()
            except Exception as e:
                logger.warning(f"[REPORTS] Não foi possível ler stat de {f}: {e}")
                continue

            modified_dt = datetime.fromtimestamp(stat.st_mtime)
            created_dt = datetime.fromtimestamp(stat.st_ctime)

            if q and q.lower() not in f.name.lower():
                continue

            if start_date:
                try:
                    sd = datetime.strptime(start_date, "%Y-%m-%d")
                    if modified_dt < sd:
                        continue
                except ValueError:
                    raise HTTPException(status_code=400, detail="start_date inválida. Use YYYY-MM-DD.")

            if end_date:
                try:
                    ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                    if modified_dt > ed:
                        continue
                except ValueError:
                    raise HTTPException(status_code=400, detail="end_date inválida. Use YYYY-MM-DD.")

            files.append(
                ReportFile(
                    filename=f.name,
                    size_bytes=stat.st_size,
                    size_human=_human_size(stat.st_size),
                    created_at=created_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    modified_at=modified_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    url_download=f"/reports/files/{f.name}",
                    url_preview=f"/reports/files/{f.name}?inline=1",
                )
            )

        files.sort(key=lambda x: x.modified_at, reverse=True)
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REPORTS] Erro ao listar arquivos: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro ao listar relatórios.")

@router.get("/reports/files/{filename}")
def get_report_file(filename: str, inline: Optional[int] = 0):
    """
    Baixa ou pré-visualiza (inline=1) um relatório PDF.
    - inline=0 (ou omitido): faz download (Content-Disposition: attachment)
    - inline=1: abre no navegador (Content-Disposition: inline)
    """
    try:
        file_path = _safe_join_strict(REPORTS_DIR, filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

        is_pdf = file_path.suffix.lower() == ".pdf"

        if inline == 1 and is_pdf:
            return FileResponse(
                path=str(file_path),
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{file_path.name}"'}
            )

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/pdf" if is_pdf else "application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REPORTS] Erro ao servir arquivo {filename}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro ao abrir relatório.")

@router.delete("/reports/files/{filename}")
def delete_report_file(filename: str):
    """
    Exclui um relatório existente (apenas PDFs).
    """
    try:
        file_path = _safe_join_strict(REPORTS_DIR, filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

        if file_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Somente PDFs podem ser excluídos.")

        file_path.unlink(missing_ok=False)
        logger.info(f"[REPORTS] Arquivo excluído: {file_path.name}")
        return {"status": "deleted", "filename": file_path.name}

    except HTTPException:
        raise
    except PermissionError as e:
        logger.error(f"[REPORTS] Sem permissão para excluir {filename}: {e}")
        raise HTTPException(status_code=423, detail="Arquivo em uso ou sem permissão para exclusão.")
    except Exception as e:
        logger.error(f"[REPORTS] Erro ao excluir {filename}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro ao excluir relatório.")

# === Enviar PDF existente por e-mail =========================

class SendFileEmailPayload(BaseModel):
    emails: Union[EmailStr, List[EmailStr]]
    hostgroup_name: Optional[str] = None
    periodo: Optional[str] = None
    analyst: Optional[str] = None
    comments: Optional[str] = None
    logo_filename: Optional[str] = None

@router.post("/reports/files/{filename}/email")
def email_existing_report(
    filename: str,
    payload: SendFileEmailPayload = Body(...),
    background_tasks: BackgroundTasks = None
):
    try:
        file_path = _safe_join_strict(REPORTS_DIR, filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        if file_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Somente PDFs podem ser enviados.")

        recipients = payload.emails if isinstance(payload.emails, list) else [payload.emails]
        if not recipients:
            raise HTTPException(status_code=400, detail="Informe ao menos um e-mail em 'emails'.")

        logo_path = get_logo_path(payload.logo_filename)

        background_tasks.add_task(
            send_report_email_sync,
            recipients=recipients,
            file_path=str(file_path),
            hostgroup_name=payload.hostgroup_name,
            periodo=payload.periodo,
            analyst=payload.analyst,
            comments=payload.comments,
            logo_path=logo_path
        )

        return {
            "status": "ok",
            "message": f"E-mail agendado para {', '.join(recipients)}",
            "filename": file_path.name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REPORTS] Erro ao enviar e-mail do arquivo {filename}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro ao agendar envio de e-mail do relatório.")

# ======================================================================================
#                                RELATÓRIO AGENDADO
# ======================================================================================

def is_first_week_of_month(date: datetime) -> bool:
    """Retorna True se a data estiver entre os 7 primeiros dias do mês."""
    return 1 <= date.day <= 7

@router.post("/reports/scheduled/run")
def run_scheduled_reports(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Força o envio mesmo que já tenha sido enviado para o período")
):
    """
    Executa relatórios agendados (weekly/monthly), atualiza datas no payload,
    injeta GLPI automaticamente, gera o PDF e agenda envio por e-mail.
    Compatível com campos extras em JSON (GLPI/ITSM).
    """
    processed = []
    try:
        config_files = sorted((CONFIG_DIR).glob("*.json"))
        logger.info(f"[AGENDADO] Executando relatórios agendados para {len(config_files)} configs (force={force})")

        today = datetime.now()

        for config_file in config_files:
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

                frequency = cfg.get("frequency")
                emails = cfg.get("emails", [])
                if not frequency or not emails:
                    logger.info(f"[AGENDADO] Ignorando {config_file.name}: sem frequência ou e-mails.")
                    continue

                # Define período
                if frequency == "monthly":
                    start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                    end_date = today.replace(day=1) - timedelta(days=1)
                    period_str = start_date.strftime("%Y-%m")
                elif frequency == "weekly":
                    start_date = today - timedelta(days=today.weekday() + 7)
                    end_date = start_date + timedelta(days=6)
                    period_str = start_date.strftime("%Y-%W")
                else:
                    logger.warning(f"[AGENDADO] Frequência desconhecida em {config_file.name}")
                    continue

                # Evita reenvio
                last_sent_period = cfg.get("last_sent_period")
                if not force and last_sent_period == period_str:
                    logger.info(f"[AGENDADO] IGNORADO: {config_file.name} já enviado para {period_str}. Use force=true.")
                    continue

                # Atualiza período dos gráficos
                for host in cfg.get("hosts", []):
                    for graph in host.get("graphs", []):
                        graph["from_time"] = start_date.strftime("%Y-%m-%d 00:00:00")
                        graph["to_time"] = end_date.strftime("%Y-%m-%d 23:59:59")

                # Injetar GLPI
                cfg = _inject_glpi_period(cfg, start_date, end_date, today)

                # Geração e envio
                logo_path = get_logo_path(cfg.get("logo_filename"))
                periodo = f"{start_date.date()} a {end_date.date()}"

                report_request = ReportRequest(**cfg)
                file_path = ReportService.generate_pdf_db(report_request, config_file=config_file)

                background_tasks.add_task(
                    send_report_email,
                    recipients=emails,
                    file_path=file_path,
                    hostgroup_name=cfg.get("hostgroup", {}).get("name"),
                    periodo=periodo,
                    analyst=cfg.get("analyst"),
                    comments=cfg.get("comments"),
                    logo_path=logo_path
                )

                # Atualiza controle
                cfg["last_sent_period"] = period_str
                cfg["last_sent"] = datetime.now().isoformat()
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)

                processed.append({
                    "filename": config_file.name,
                    "report_file": file_path,
                    "emails_sent": emails,
                    "last_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "force": force
                })

            except Exception as e:
                logger.error(f"[AGENDADO] Erro ao processar {config_file.name}: {e}\n{traceback.format_exc()}")
                continue

        if not processed:
            logger.info("[AGENDADO] Nenhum relatório agendado executado neste ciclo.")
            return {"status": "no_reports", "message": "Nenhum relatório agendado para executar."}

        logger.info(f"[AGENDADO] Relatórios agendados executados. Total: {len(processed)}")
        return {"status": "ok", "processed": processed}

    except Exception as e:
        logger.error(f"[AGENDADO] Erro geral: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao executar relatórios agendados: {str(e)}")

# ======================================================================================
#                         GERAR PDF DB (STREAMING/ANEXO)
# ======================================================================================

@router.post("/reports/pdf/db")
async def generate_pdf_report_db(request: Request):
    """
    Gera um relatório PDF utilizando dados do payload (Zabbix/GLPI/ITSM),
    injeta GLPI automaticamente quando aplicável, e retorna o PDF como anexo.
    Aceita dois formatos de body:
      - { "data": { ...estrutura do relatório... }, "recipient": [...] }
      - { ...estrutura do relatório diretamente... }
    """
    try:
        body = await request.json()
        report_data = body.get("data", body)

        # Extrai período global a partir do primeiro gráfico para basear o GLPI
        hosts = report_data.get("hosts") or []
        if not hosts or not hosts[0].get("graphs"):
            raise HTTPException(status_code=400, detail="Nenhum gráfico informado.")
        first_g = hosts[0]["graphs"][0]
        start_date = datetime.fromisoformat(str(first_g["from_time"]).replace(" ", "T"))
        end_date = datetime.fromisoformat(str(first_g["to_time"]).replace(" ", "T"))

        # Injeta GLPI
        cfg = _inject_glpi_period(dict(report_data), start_date, end_date)

        file_path = ReportService.generate_pdf_db(cfg)
        pdf_file = Path(file_path)
        if not pdf_file.exists():
            raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado após geração")
        return StreamingResponse(
            pdf_file.open("rb"),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_file.name}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Erro ao gerar PDF DB: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF DB: {str(e)}")
