# app/glpi/routes.py

from fastapi import APIRouter, Query
from app.glpi import services
from app.core.logging import logger

router = APIRouter(prefix="/glpi", tags=["GLPI"])


@router.get("/relatorio")
def gerar_relatorio_glpi(entidade_id: int, inicio: str, fim: str):
    """
    Gera relatório completo dos chamados de uma entidade entre as datas.
    """
    try:
        tempos = services.get_tempo_chamados(entidade_id, inicio, fim)
        tratados = services.get_chamados_bi(entidade_id, inicio, fim)
        usuarios = services.get_usuarios_entidade(entidade_id)
        evolutivo = services.get_evolutivo(entidade_id)
        evolutivo_tratados = services.get_evolutivo_tratados(entidade_id)
        metricas = services.processar_metrica_chamados(tratados)

        return {
            "entidade_id": entidade_id,
            "periodo": {"inicio": inicio, "fim": fim},
            "chamados_detalhados": tempos,
            "usuarios": usuarios,
            "evolutivo_abertura": evolutivo,
            "evolutivo_tratados": evolutivo_tratados,
            "metricas": metricas
        }
    except Exception as e:
        logger.error(f"[GLPI] Erro ao gerar relatório: {str(e)}")
        return {"erro": str(e)}
