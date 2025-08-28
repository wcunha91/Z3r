# app/zabbix/db_service.py

import pymysql
from datetime import datetime
from app.core.config import MYSQL_HOST, MYSQL_USER, MYSQL_PASS, MYSQL_DB
from app.core.logging import logger

def get_db_connection():
    """Conexão com o banco MySQL do Zabbix."""
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_metrics_by_item(itemid: int, from_time: str, to_time: str):
    """Consulta a view v_zabbix_metrics para valores do gráfico."""
    query = """
        SELECT clock, value
        FROM v_zabbix_metrics
        WHERE itemid = %s
          AND clock BETWEEN %s AND %s
        ORDER BY clock ASC
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (itemid, from_time, to_time))
            results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"Erro ao buscar métricas do banco: {str(e)}")
        raise
    finally:
        conn.close()

def get_item_value_type(itemid):
    """
    Busca o value_type do item.
    Retorna um inteiro correspondente ao tipo (0=float, 1=str, 2=log, 3=uint, 4=text)
    """
    query = "SELECT value_type FROM items WHERE itemid = %s"
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (itemid,))
            result = cursor.fetchone()
        if not result:
            logger.warning(f"[ZABBIX] Item {itemid} não encontrado para busca do value_type.")
            return None
        return result['value_type']
    except Exception as e:
        logger.error(f"[ZABBIX] Erro ao buscar value_type do item {itemid}: {str(e)}")
        return None
    finally:
        conn.close()

def get_item_metrics(itemid, from_time, to_time,):
    """
    Busca o histórico de um item, automaticamente escolhendo a tabela de acordo com o tipo do dado.
    Sempre retorna lista de dicts: {itemid, item_name, data_coleta, value, value_type, tipo_str}
    """
    value_type = get_item_value_type(itemid)
    if value_type is None:
        logger.warning(f"[ZABBIX] value_type não encontrado para itemid {itemid}.")
        return []

    type_map = {
        0: ('history',       'float'),
        1: ('history_str',   'str'),
        2: ('history_log',   'log'),
        3: ('history_uint',  'uint'),
        4: ('history_text',  'text')
    }
    if value_type not in type_map:
        logger.error(f"[ZABBIX] value_type {value_type} desconhecido para itemid {itemid}.")
        return []
    table, tipo_str = type_map[value_type]

    query = f"""
        SELECT 
            h.itemid, 
            i.name AS item_name,
            FROM_UNIXTIME(h.clock) AS data_coleta,
            h.value,
            i.value_type
        FROM {table} h
        JOIN items i ON h.itemid = i.itemid
        WHERE h.itemid = %s 
          AND h.clock BETWEEN UNIX_TIMESTAMP(%s) AND UNIX_TIMESTAMP(%s)
        ORDER BY h.clock DESC
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            logger.info(f"[ZABBIX] Buscando dados do item {itemid} ({tipo_str}) entre {from_time} e {to_time} na tabela {table}.")
            cursor.execute(query, (itemid, from_time, to_time))
            rows = cursor.fetchall()
            for r in rows:
                r['tipo_str'] = tipo_str
        logger.info(f"[ZABBIX] {len(rows)} registros retornados para item {itemid}.")
        return rows
    except Exception as e:
        logger.error(f"[ZABBIX] Erro ao buscar dados do item {itemid} na tabela {table}: {str(e)}")
        return []
    finally:
        conn.close()

def get_last_value_of_item(itemid):
    """
    Retorna o último valor de um item (qualquer tipo). Para texto, retorna apenas o último.
    Para numéricos, retorna todos os pontos do período.
    """
    value_type = get_item_value_type(itemid)
    if value_type is None:
        return None

    # Para texto/str/log (1, 2, 4), busca só o último
    if value_type in [1, 2, 4]:
        type_map = {
            1: 'history_str',
            2: 'history_log',
            4: 'history_text'
        }
        table = type_map.get(value_type)
        query = f"""
            SELECT h.itemid, i.name AS item_name, FROM_UNIXTIME(h.clock) AS data_coleta, h.value
            FROM {table} h
            JOIN items i ON h.itemid = i.itemid
            WHERE h.itemid = %s
            ORDER BY h.clock DESC
            LIMIT 1
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (itemid,))
                row = cursor.fetchone()
            return row
        finally:
            conn.close()
    else:
        return get_item_metrics(itemid, '1970-01-01 00:00:00', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 100)

def get_items_by_graph(graph_id: int):
    """
    Retorna todos os itens (itemid, item_name) associados a um gráfico.
    Importante para plotar todos os dados de um gráfico do Zabbix no PDF/Streamlit.
    """
    query = """
        SELECT gi.itemid, i.name as item_name
        FROM graphs_items gi
        JOIN items i ON gi.itemid = i.itemid
        WHERE gi.graphid = %s
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (graph_id,))
            rows = cursor.fetchall()
            return [{"itemid": r["itemid"], "item_name": r["item_name"]} for r in rows]
    except Exception as e:
        logger.error(f"Erro ao buscar itens do gráfico {graph_id}: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()
