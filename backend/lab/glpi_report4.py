import pymysql
from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import Counter

# Configuração da conexão com o banco
DB_CONFIG = {
    "host": "164.152.255.250",
    "port": 3306,
    "user": "glpi_reader",
    "password": "b5Gtf6464&0nN3",
    "db": "glpi",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

ENTIDADE_ID = 1
DATA_INICIO = "2025-07-01"
DATA_FIM = "2025-07-31"

# Mapeamento de status do GLPI
STATUS_MAP = {
    1: "Novo",
    2: "Em andamento (atribuído)",
    3: "Em andamento (planejado)",
    4: "Pendente",
    5: "Resolvido",
    6: "Fechado"
}


def conectar():
    """Estabelece a conexão com o banco de dados."""
    return pymysql.connect(**DB_CONFIG)


def obter_nome_entidade(conn, entidade_id):
    """Busca o nome da entidade a partir do ID."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT name FROM glpi_entities WHERE id = %s", (entidade_id,))
        row = cursor.fetchone()
        return row["name"] if row else f"Entidade {entidade_id}"


def obter_tempos_chamados(conn, entidade_id, data_inicio, data_fim):
    """Consulta os tempos detalhados da viewTempoChamadoDetalhado."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM viewTempoChamadoDetalhado
            WHERE entidade_id = %s
              AND data_abertura BETWEEN %s AND %s
        """, (entidade_id, data_inicio, data_fim))
        return cursor.fetchall()


def obter_tickets_tratados(conn, entidade_id, data_inicio, data_fim):
    """Consulta os tickets tratados na viewGLPIBI para a entidade informada."""
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
    """Gera o evolutivo de chamados com base na data de abertura."""
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
    """Gera o evolutivo de chamados com base na data de tratamento (GLPIBI)."""
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
    """Retorna os usuários autorizados da entidade (nome, login, email)."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT nome, login, email
            FROM viewUsuariosEntidade
            WHERE entidade_id = %s
        """, (entidade_id,))
        return cursor.fetchall()


def processar_metrica_glpibi(tickets):
    """Gera métricas agregadas a partir dos dados da viewGLPIBI."""
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


def exibir_relatorio(entidade_nome, tempos, evolutivo, usuarios, glpi_metrica, glpi_evolucao):
    """Exibe o relatório final com base nos dados consolidados."""
    print(f"\n📊 Relatório Completo: {entidade_nome} (ID {ENTIDADE_ID})")
    print(f"Período: {DATA_INICIO} até {DATA_FIM}")
    print("-" * 60)

    total_tickets = len(tempos)
    tempos_atribuicao = [t['tempo_ate_atribuicao_minutos'] for t in tempos if t['tempo_ate_atribuicao_minutos']]
    media_atribuicao = sum(tempos_atribuicao) / len(tempos_atribuicao) if tempos_atribuicao else 0

    tempos_pendencia = [t['tempo_pendencia_minutos'] for t in tempos if t['tempo_pendencia_minutos']]
    media_pendencia = sum(tempos_pendencia) / len(tempos_pendencia) if tempos_pendencia else 0

    tempos_sla_util = [t['tempo_sla_util_minutos'] for t in tempos if t['tempo_sla_util_minutos']]
    media_sla_util = sum(tempos_sla_util) / len(tempos_sla_util) if tempos_sla_util else 0

    tempos_tarefas = [t['tempo_tarefas_minutos'] for t in tempos if t['tempo_tarefas_minutos']]
    media_tarefas = sum(tempos_tarefas) / len(tempos_tarefas) if tempos_tarefas else 0

    print(f"Total de chamados (viewTempoChamadoDetalhado): {total_tickets}")
    print(f"Média tempo até atribuição: {media_atribuicao:.2f} min")
    print(f"Média tempo pendência: {media_pendencia:.2f} min")
    print(f"Média tempo SLA útil: {media_sla_util:.2f} min")
    print(f"Média tempo real das tarefas: {media_tarefas:.2f} min")

    print("\n📈 Evolutivo por tempo de abertura:")
    for e in evolutivo:
        print(f"  {e['mes']}: {e['total']} tickets")

    print("\n📋 Tickets detalhados (viewTempoChamadoDetalhado):")
    for t in tempos:
        if t['tempo_total_minutos'] is not None and t['tempo_sla_util_minutos'] is not None:
            sla_status = "Cumprido" if t['tempo_total_minutos'] <= t['tempo_sla_util_minutos'] else "Violado"
        else:
            sla_status = "Indefinido"
        status_nome = STATUS_MAP.get(t['status'], f"Status {t['status']}")
        print(f"  [{t['id_chamado']}] {t['titulo']} - Abertura: {t['data_abertura']} | Status: {status_nome} | SLA: {sla_status} | Total: {t['tempo_total_minutos']} min")

    print("\n👥 Usuários autorizados:")
    for u in usuarios:
        print(f"  {u['nome']} ({u['login']}) - {u['email']}")

    print("\n🔍 Visão complementar (viewGLPIBI):")
    print(f"Total tratados: {glpi_metrica['total']}")
    print(f"Média de resolução: {glpi_metrica['media_duracao_horas']}h")

    print("\nStatus dos chamados:")
    for s, c in glpi_metrica["status"].items():
        print(f"  {STATUS_MAP.get(s, f'Status {s}')}: {c}")

    print("\nTop Técnicos:")
    for t, c in glpi_metrica["tecnicos"]:
        print(f"  {t}: {c} tickets")

    print("\nTop Categorias:")
    for cat, c in glpi_metrica["categorias"]:
        print(f"  {cat}: {c}")

    print("\nTickets por Origem:")
    for origem, c in glpi_metrica["origens"].items():
        print(f"  {origem}: {c}")

    print("\n📅 Evolutivo - viewGLPIBI:")
    for mes in glpi_evolucao:
        print(f"  {mes['mes']}: {mes['qtd']} tickets")

    print("\n📋 Tabela de tickets tratados:")
    for t in glpi_metrica["tickets_detalhados"]:
        print(f"  {t['id_chamado']} | {STATUS_MAP.get(t['status'], t['status'])} | {t['tecnico']} | {t['categoria']} | {t['data_abertura']} → {t['data_solucao'] or '...'}")


def main():
    try:
        conn = conectar()

        entidade_nome = obter_nome_entidade(conn, ENTIDADE_ID)
        tempos = obter_tempos_chamados(conn, ENTIDADE_ID, DATA_INICIO, DATA_FIM)
        evolutivo = obter_evolutivo_chamados(conn, ENTIDADE_ID)
        usuarios = obter_usuarios_entidade(conn, ENTIDADE_ID)

        glpi_tickets = obter_tickets_tratados(conn, ENTIDADE_ID, DATA_INICIO, DATA_FIM)
        glpi_evolucao = obter_evolutivo_tratados(conn, ENTIDADE_ID)
        glpi_metrica = processar_metrica_glpibi(glpi_tickets)

        exibir_relatorio(entidade_nome, tempos, evolutivo, usuarios, glpi_metrica, glpi_evolucao)

    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
