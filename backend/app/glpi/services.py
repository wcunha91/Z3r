# app/glpi/services.py

from collections import Counter
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from app.glpi.db_service import get_glpi_db_connection
from app.core.logging import logger

# Mapeamento de status dos tickets (GLPI)
STATUS_MAP = {
    1: "Novo",
    2: "Em andamento",
    3: "Atividade Planejada",
    4: "Aguardando Cliente",
    5: "Fechado",
    6: "Fechado",
    7: "Planejado",
    8: "Resolvido",
    9: "Recusado"
}


def get_tempo_chamados(entidade_id, inicio, fim):
    """Consulta os tempos dos chamados detalhados da entidade."""
    query = """
        SELECT *
        FROM viewTempoChamadoDetalhado
        WHERE entidade_id = %s AND data_abertura BETWEEN %s AND %s
    """
    with get_glpi_db_connection().cursor() as cursor:
        cursor.execute(query, (entidade_id, inicio, fim))
        return cursor.fetchall()


def get_chamados_bi(entidade_id, inicio, fim):
    """Consulta chamados GLPI tratados no período (viewGLPIBI)."""
    query = """
        SELECT id_chamado, status, tipo, categoria, tecnico, requerente,
               data_abertura, data_solucao, duracao_total, duracao_horas,
               origem_requisicao, tempo_solucao_excedido
        FROM viewGLPIBI
        WHERE entidade_id = %s AND (
            data_abertura BETWEEN %s AND %s OR
            data_solucao BETWEEN %s AND %s
        )
    """
    with get_glpi_db_connection().cursor() as cursor:
        cursor.execute(query, (entidade_id, inicio, fim, inicio, fim))
        return cursor.fetchall()


def get_evolutivo(entidade_id, meses=6):
    """Retorna a evolução de chamados por mês (abertura)."""
    data_inicio = (datetime.now() - relativedelta(months=meses-1)).replace(day=1)
    query = """
        SELECT DATE_FORMAT(data_abertura, '%%Y-%%m') as mes, COUNT(*) as total
        FROM viewTempoChamadoDetalhado
        WHERE entidade_id = %s AND data_abertura >= %s
        GROUP BY mes ORDER BY mes
    """
    with get_glpi_db_connection().cursor() as cursor:
        cursor.execute(query, (entidade_id, data_inicio.strftime('%Y-%m-%d')))
        return cursor.fetchall()


def get_evolutivo_tratados(entidade_id, meses=6):
    """Evolução dos chamados tratados por mês."""
    data_inicio = (datetime.now() - relativedelta(months=meses-1)).replace(day=1)
    query = """
        SELECT DATE_FORMAT(data_abertura, '%%Y-%%m') as mes, COUNT(*) as qtd
        FROM viewGLPIBI
        WHERE entidade_id = %s AND data_abertura >= %s
        GROUP BY mes ORDER BY mes
    """
    with get_glpi_db_connection().cursor() as cursor:
        cursor.execute(query, (entidade_id, data_inicio.strftime('%Y-%m-%d')))
        return cursor.fetchall()


def get_usuarios_entidade(entidade_id):
    """Lista os usuários autorizados para a entidade."""
    query = """
        SELECT nome, login, email
        FROM viewUsuariosEntidade
        WHERE entidade_id = %s
    """
    with get_glpi_db_connection().cursor() as cursor:
        cursor.execute(query, (entidade_id,))
        return cursor.fetchall()


def processar_metrica_chamados(lista):
    """Processa métricas dos chamados tratados."""
    status = Counter([ch["status"] for ch in lista])
    tecnicos = Counter([ch["tecnico"] for ch in lista if ch["tecnico"]])
    categorias = Counter([ch["categoria"] for ch in lista if ch["categoria"]])
    origens = Counter([ch["origem_requisicao"] for ch in lista if ch["origem_requisicao"]])
    duracoes = [int(ch["duracao_total"]) for ch in lista if ch["duracao_total"]]

    media_duracao = round(sum(duracoes) / len(duracoes), 2) if duracoes else 0
    media_horas = round(media_duracao / 60, 2)

    return {
        "total": len(lista),
        "status": {STATUS_MAP.get(k, k): v for k, v in status.items()},
        "tecnicos": tecnicos.most_common(5),
        "categorias": categorias.most_common(5),
        "origens": origens,
        "media_duracao_horas": media_horas,
        "detalhado": lista
    }
