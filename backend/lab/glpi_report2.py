import pymysql
from collections import Counter, defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar


# Configurações de conexão
#DB_HOST = "164.152.255.250"
#DB_PORT = 3306
#DB_USER = "glpi_reader"
#DB_PASSWORD = "b5Gtf6464&0nN3"
#DB_NAME = "glpi"

# Configuração
DB_CONFIG = {
    "host": "164.152.255.250",
    "port": 3306,
    "user": "glpi_reader",
    "password": "b5Gtf6464&0nN3",
    "db": "glpi",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

ENTIDADE = "Athena Security"
DATA_INICIO = "2025-07-01"
DATA_FIM = "2025-07-31"

def conectar():
    return pymysql.connect(**DB_CONFIG)

def obter_tickets_tratados(conn):
    with conn.cursor() as cursor:
        query = """
        SELECT id_chamado, status, tipo, categoria, tecnico, requerente,
               data_abertura, data_solucao, duracao_total, duracao_horas, origem_requisicao
        FROM viewGLPIBI
        WHERE entidade = %s
        AND (
            (data_abertura BETWEEN %s AND %s)
            OR (data_solucao BETWEEN %s AND %s)
        )
        """
        cursor.execute(query, (ENTIDADE, DATA_INICIO, DATA_FIM, DATA_INICIO, DATA_FIM))
        return cursor.fetchall()

def obter_evolutivo_tratados(conn, meses=6):
    hoje = datetime.now()
    inicio_base = (hoje - relativedelta(months=meses-1)).replace(day=1)

    with conn.cursor() as cursor:
        query = """
        SELECT DATE_FORMAT(data_abertura, '%%Y-%%m') as mes, COUNT(*) as qtd
        FROM viewGLPIBI
        WHERE entidade = %s
        AND data_abertura >= %s
        GROUP BY mes
        ORDER BY mes
        """
        cursor.execute(query, (ENTIDADE, inicio_base.strftime("%Y-%m-%d")))
        return cursor.fetchall()

def processar_metrica(tickets):
    status = Counter([t["status"] for t in tickets])
    tecnicos = Counter([t["tecnico"] for t in tickets if t["tecnico"]])
    categorias = Counter([t["categoria"] for t in tickets if t["categoria"]])
    origens = Counter([t["origem_requisicao"] for t in tickets if t["origem_requisicao"]])
    duracoes = [int(t["duracao_total"]) for t in tickets if t["duracao_total"] and int(t["duracao_total"]) > 0]

    media_duracao = sum(duracoes) / len(duracoes) if duracoes else 0
    media_horas = round(media_duracao / 3600, 2)  # em horas

    return {
        "total": len(tickets),
        "status": status,
        "tecnicos": tecnicos.most_common(5),
        "categorias": categorias.most_common(5),
        "origens": origens,
        "media_duracao_horas": media_horas,
        "tickets_detalhados": tickets
    }

def exibir_relatorio(m, evolutivo):
    print(f"\n📊 Relatório: {ENTIDADE}")
    print(f"Período: {DATA_INICIO} a {DATA_FIM}")
    print("-" * 50)
    print(f"Total de tickets tratados: {m['total']}")
    print(f"Média de resolução (horas): {m['media_duracao_horas']}h\n")

    print("Tickets por Status:")
    for s, c in m["status"].items():
        print(f"  Status {s}: {c}")

    print("\nTop Técnicos:")
    for t, c in m["tecnicos"]:
        print(f"  {t}: {c} tickets")

    print("\nTop Categorias:")
    for cat, c in m["categorias"]:
        print(f"  {cat}: {c}")

    print("\nTickets por Origem:")
    for origem, c in m["origens"].items():
        print(f"  {origem}: {c}")

    print("\n📅 Evolutivo - Abertura por mês:")
    for mes in evolutivo:
        print(f"  {mes['mes']}: {mes['qtd']} tickets")

    print("\n📋 Tabela de tickets tratados:")
    for t in m["tickets_detalhados"]:
        print(f"  {t['id_chamado']} | {t['status']} | {t['tecnico']} | {t['categoria']} | {t['data_abertura']} → {t['data_solucao'] or '...' }")

def main():
    try:
        conn = conectar()
        tickets = obter_tickets_tratados(conn)
        evolucao = obter_evolutivo_tratados(conn)
        metrica = processar_metrica(tickets)
        exibir_relatorio(metrica, evolucao)
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
