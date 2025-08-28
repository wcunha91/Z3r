import pymysql
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

# Lê as variáveis de conexão do banco GLPI
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOSTGLPI"),
    "user": os.getenv("MYSQL_USERGLPI"),
    "password": os.getenv("MYSQL_PASSGLPI"),
    "db": os.getenv("MYSQL_DBGLPI"),
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

STATUS_MAP = {
    1: "Novo",
    2: "Em andamento (atribuído)",
    3: "Em andamento (planejado)",
    4: "Pendente",
    5: "Resolvido",
    6: "Fechado"
}

def conectar():
    """Estabelece conexão com o banco de dados MySQL (GLPI)."""
    return pymysql.connect(**DB_CONFIG)

def obter_nome_entidade(conn, entidade_id):
    """Retorna o nome da entidade com base no ID."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT name FROM glpi_entities WHERE id = %s", (entidade_id,))
        row = cursor.fetchone()
        return row["name"] if row else f"Entidade {entidade_id}"

def obter_tempos_chamados(conn, entidade_id, data_inicio, data_fim):
    """Retorna os tempos detalhados por chamado da view viewTempoChamadoDetalhado."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM viewTempoChamadoDetalhado
            WHERE entidade_id = %s
              AND data_abertura BETWEEN %s AND %s
        """, (entidade_id, data_inicio, data_fim))
        return cursor.fetchall()

def obter_tickets_tratados(conn, entidade_id, data_inicio, data_fim):
    """Retorna os tickets tratados no mês com base na view viewGLPIBI."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM viewGLPIBI
            WHERE entidade_id = %s
              AND (
                  (data_abertura BETWEEN %s AND %s)
                  OR (data_solucao BETWEEN %s AND %s)
              )
        """, (entidade_id, data_inicio, data_fim, data_inicio, data_fim))
        return cursor.fetchall()

def obter_evolutivo_chamados(conn, entidade_id, meses=6):
    """Retorna o total de chamados abertos por mês."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    inicio = (datetime.now() - relativedelta(months=meses-1)).replace(day=1)

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT DATE_FORMAT(data_abertura, '%%Y-%%m') as mes,
                   COUNT(*) as total
            FROM viewTempoChamadoDetalhado
            WHERE entidade_id = %s
              AND data_abertura >= %s
            GROUP BY mes
            ORDER BY mes
        """, (entidade_id, inicio.strftime('%Y-%m-%d')))
        return cursor.fetchall()

def obter_evolutivo_tratados(conn, entidade_id, meses=6):
    """Retorna o total de chamados tratados por mês."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    inicio = (datetime.now() - relativedelta(months=meses-1)).replace(day=1)

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT DATE_FORMAT(data_abertura, '%%Y-%%m') as mes, COUNT(*) as qtd
            FROM viewGLPIBI
            WHERE entidade_id = %s
              AND data_abertura >= %s
            GROUP BY mes
            ORDER BY mes
        """, (entidade_id, inicio.strftime("%Y-%m-%d")))
        return cursor.fetchall()

def obter_usuarios_entidade(conn, entidade_id):
    """Retorna os usuários com permissão na entidade."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT nome, login, email
            FROM viewUsuariosEntidade
            WHERE entidade_id = %s
        """, (entidade_id,))
        return cursor.fetchall()

def processar_metrica_glpibi(tickets):
    """Processa os tickets tratados e retorna métricas resumidas."""
    from collections import Counter
    status = Counter([t["status"] for t in tickets])
    tecnicos = Counter([t["tecnico"] for t in tickets if t["tecnico"]])
    categorias = Counter([t["categoria"] for t in tickets if t["categoria"]])
    origens = Counter([t["origem_requisicao"] for t in tickets if t["origem_requisicao"]])
    duracoes = [int(t["duracao_total"]) for t in tickets if t["duracao_total"] and int(t["duracao_total"]) > 0]

    media_duracao = sum(duracoes) / len(duracoes) if duracoes else 0
    media_horas = round(media_duracao / 60, 2)

    return {
        "total": len(tickets),
        "status": status,
        "tecnicos": tecnicos.most_common(5),
        "categorias": categorias.most_common(5),
        "origens": origens,
        "media_duracao_horas": media_horas,
        "tickets_detalhados": tickets
    }
