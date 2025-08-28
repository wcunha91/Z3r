"""
Script isolado para extração de métricas da viewGLPIBI.
Requer pymysql instalado e acesso ao banco MySQL do GLPI.
"""

import pymysql
from collections import Counter
from datetime import datetime

# Configurações de conexão
DB_HOST = "164.152.255.250"
DB_PORT = 3306
DB_USER = "glpi_reader"
DB_PASSWORD = "b5Gtf6464&0nN3"
DB_NAME = "glpi"

# Filtros
ENTIDADE = "Catupiry"
DATA_INICIO = "2025-07-01"
DATA_FIM = "2025-07-31"

def conectar():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def obter_dados(conexao):
    with conexao.cursor() as cursor:
        query = """
        SELECT status, tecnico, categoria, tempo_solucao_excedido
        FROM viewGLPIBI
        WHERE entidade = %s
          AND data_abertura BETWEEN %s AND %s
        """
        cursor.execute(query, (ENTIDADE, DATA_INICIO, DATA_FIM))
        return cursor.fetchall()

def processar(dados):
    total = len(dados)
    status_contagem = Counter([d["status"] for d in dados])
    tecnicos = Counter([d["tecnico"] for d in dados if d["tecnico"]])
    categorias = Counter([d["categoria"] for d in dados if d["categoria"]])
    sla_estourado = sum(1 for d in dados if d["tempo_solucao_excedido"] and int(d["tempo_solucao_excedido"]) > 0)

    return {
        "total_tickets": total,
        "status": status_contagem,
        "sla_estourado": sla_estourado,
        "top_tecnicos": tecnicos.most_common(5),
        "top_categorias": categorias.most_common(5)
    }

def exibir_metrica(metrica):
    print(f"\n📊 Relatório de Métricas — Entidade: {ENTIDADE}")
    print(f"Período: {DATA_INICIO} até {DATA_FIM}")
    print("-" * 50)
    print(f"Total de tickets: {metrica['total_tickets']}")
    print(f"Tickets com SLA estourado: {metrica['sla_estourado']}")
    print("\nTickets por Status:")
    for status, count in metrica["status"].items():
        print(f"  Status {status}: {count} tickets")

    print("\nTop Técnicos:")
    for tecnico, count in metrica["top_tecnicos"]:
        print(f"  {tecnico}: {count} tickets")

    print("\nTop Categorias:")
    for categoria, count in metrica["top_categorias"]:
        print(f"  {categoria}: {count} tickets")

if __name__ == "__main__":
    try:
        conn = conectar()
        dados = obter_dados(conn)
        metricas = processar(dados)
        exibir_metrica(metricas)
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()
