# app/zabbix/routes.py

from fastapi import APIRouter, HTTPException, Query, Request
from app.zabbix.service import ZabbixService
from app.core.logging import logger
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime
from app.zabbix.db_service import get_db_connection
from app.zabbix.db_service import get_item_metrics, get_item_value_type
from app.core.config import ZABBIX_API_URL, ZABBIX_WEB_URL, ZABBIX_USER, ZABBIX_PASS
router = APIRouter()

@router.get("/zabbix/version")
def check_zabbix_version(api_url: str = Query(..., description="URL da API JSON-RPC do Zabbix")):
    """
    Retorna a versão da API do Zabbix para validar conectividade.
    """
    try:
        version = ZabbixService.get_version(api_url)
        return {"zabbix_version": version}
    except Exception as e:
        logger.error(f"Falha ao consultar Zabbix: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar Zabbix: {str(e)}")

@router.get("/zabbix/test-auth")
def test_auth_env():
    """
    Testa autenticação utilizando os dados do .env
    """
    results = {}
    try:
        version = ZabbixService.get_version(ZABBIX_API_URL)
        results["version"] = version
    except Exception as e:
        results["version"] = f"Erro: {str(e)}"

    try:
        token = ZabbixService.authenticate_api(ZABBIX_API_URL, ZABBIX_USER, ZABBIX_PASS)
        results["api_auth"] = {"status": "ok", "token": token}
    except Exception as e:
        results["api_auth"] = {"status": "erro", "mensagem": str(e)}

    try:
        cookie = ZabbixService.authenticate_web(ZABBIX_WEB_URL, ZABBIX_USER, ZABBIX_PASS)
        results["web_auth"] = {"status": "ok", "cookie": cookie}
    except Exception as e:
        results["web_auth"] = {"status": "erro", "mensagem": str(e)}

    return results

@router.get("/zabbix/hostgroups")
def get_hostgroups():
    """
    Retorna a lista de hostgroups disponíveis no Zabbix.
    Utiliza credenciais do .env.
    """
    try:
        auth = ZabbixService.authenticate(
            ZABBIX_API_URL,
            ZABBIX_WEB_URL,
            ZABBIX_USER,
            ZABBIX_PASS
        )

        hostgroups = ZabbixService.list_hostgroups(
            ZABBIX_API_URL,
            auth_token=auth["api_token"],
            version=auth["version"]
        )
        return hostgroups
    except Exception as e:
        logger.error(f"Erro ao buscar hostgroups: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar hostgroups")

@router.get("/zabbix/hosts")
def get_hosts_by_group(group_id: str = Query(..., description="ID do hostgroup")):
    """
    Retorna os hosts vinculados a um hostgroup específico.
    Utiliza credenciais e versão do .env.
    """
    try:
        auth = ZabbixService.authenticate(
            ZABBIX_API_URL,
            ZABBIX_WEB_URL,
            ZABBIX_USER,
            ZABBIX_PASS
        )

        hosts = ZabbixService.list_hosts_by_group(
            api_url=ZABBIX_API_URL,
            auth_token=auth["api_token"],
            version=auth["version"],
            group_id=group_id
        )
        return hosts
    except Exception as e:
        logger.error(f"Erro ao buscar hosts do grupo {group_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar hosts do grupo")

@router.get("/zabbix/graphs")
def get_graphs_by_host(host_id: str = Query(..., description="ID do host")):
    """
    Retorna os gráficos vinculados a um host.
    Utiliza credenciais e versão do .env.
    """
    try:
        auth = ZabbixService.authenticate(
            ZABBIX_API_URL,
            ZABBIX_WEB_URL,
            ZABBIX_USER,
            ZABBIX_PASS
        )

        graphs = ZabbixService.list_graphs_by_host(
            api_url=ZABBIX_API_URL,
            auth_token=auth["api_token"],
            version=auth["version"],
            host_id=host_id
        )
        return graphs
    except Exception as e:
        logger.error(f"Erro ao buscar gráficos do host {host_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar gráficos do host")



####http://127.0.0.1:8000/zabbix/graphs/image?graph_id=3192&from_time=2025-06-29%2023:00:00&to_time=2025-06-30%2005:00:00
@router.get("/zabbix/graphs/image")
def get_graph_image(
    graph_id: str = Query(...),
    from_time: str = Query(..., description="Formato: YYYY-MM-DD HH:MM:SS"),
    to_time: str = Query(..., description="Formato: YYYY-MM-DD HH:MM:SS"),
    width: int = Query(900),
    height: int = Query(200)
):
    """
    Retorna a imagem PNG de um gráfico do Zabbix.
    """
    try:
        auth = ZabbixService.authenticate(
            ZABBIX_API_URL,
            ZABBIX_WEB_URL,
            ZABBIX_USER,
            ZABBIX_PASS
        )

        image_bytes = ZabbixService.get_graph_image(
            web_url=ZABBIX_WEB_URL,
            auth_token=auth["web_cookie"],
            graph_id=graph_id,
            from_time=from_time,
            to_time=to_time,
            width=width,
            height=height
        )

        return StreamingResponse(BytesIO(image_bytes), media_type="image/png")
    except Exception as e:
        logger.error(f"Erro ao buscar imagem do gráfico {graph_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar imagem do gráfico")


###Rotas baseadas no DB

@router.get("/zabbix/db/graph-data")
def get_graph_data_from_db(
    itemid: int = Query(..., description="ID do item (gráfico) na view"),
    from_time: str = Query(None, description="YYYY-MM-DD HH:MM:SS"),
    to_time: str = Query(None, description="YYYY-MM-DD HH:MM:SS")
):
    """
    Retorna dados do gráfico direto do banco para plotagem no frontend.
    Para itens numéricos retorna lista de pontos, para itens texto/log/str retorna só o último valor.
    """
    from app.zabbix.db_service import get_item_value_type, get_item_metrics, get_last_value_of_item
    try:
        value_type = get_item_value_type(itemid)
        if value_type is None:
            raise HTTPException(status_code=404, detail="Item não encontrado ou sem value_type.")

        # Para texto/log/str, só último valor
        if value_type in [1, 2, 4]:
            from app.zabbix.db_service import get_last_value_of_item
            logger.info(f"[ZABBIX] Item {itemid} é texto/log/str. Retornando apenas último valor.")
            result = get_last_value_of_item(itemid)
            return {"last_value": result}

        # Para numéricos, retorna lista de pontos (para gráfico)
        # Se não passou intervalo, busca últimos 100 pontos
        if not from_time or not to_time:
            from datetime import datetime, timedelta
            to_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            from_time = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        from app.zabbix.db_service import get_item_metrics
        logger.info(f"[ZABBIX] Item {itemid} é numérico. Buscando histórico para gráfico.")
        data = get_item_metrics(itemid, from_time, to_time, limit=1000)
        return {"data": data}
    except Exception as e:
        logger.error(f"Erro ao buscar dados do gráfico DB: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dados do gráfico no banco")


@router.get("/zabbix/db/test-conn")
def test_db_connection():
    """Testa conexão com o banco MySQL do Zabbix."""
    from app.zabbix.db_service import get_db_connection
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "ok", "message": "Conexão ao banco bem-sucedida"}
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")


@router.get("/zabbix/db/hostgroups")
def get_hostgroups_from_db():
    """
    Retorna a lista de hostgroups disponíveis diretamente do banco de dados.
    """
    query = """
        SELECT DISTINCT hostgroup_id, hostgroup_name
        FROM v_zabbix
        ORDER BY hostgroup_name
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        return {"hostgroups": results}
    except Exception as e:
        logger.error(f"Erro ao buscar hostgroups do banco: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar hostgroups do banco")
    finally:
        conn.close()

@router.get("/zabbix/db/hosts")
def get_hosts_from_db(hostgroup_id: int = Query(..., description="ID do hostgroup")):
    """
    Retorna os hosts de um hostgroup específico diretamente do banco de dados.
    """
    query = """
        SELECT DISTINCT host_id, host_name
        FROM v_zabbix
        WHERE hostgroup_id = %s
        ORDER BY host_name
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (hostgroup_id,))
            results = cursor.fetchall()
        return {"hosts": results}
    except Exception as e:
        logger.error(f"Erro ao buscar hosts do banco: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar hosts do banco")
    finally:
        conn.close()

@router.get("/zabbix/db/items")
def get_items_from_db(host_id: int = Query(..., description="ID do host")):
    """
    Retorna os itens de um host específico diretamente do banco de dados.
    """
    query = """
        SELECT DISTINCT item_id, item_name
        FROM v_zabbix
        WHERE host_id = %s
        ORDER BY item_name
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (host_id,))
            results = cursor.fetchall()
        return {"items": results}
    except Exception as e:
        logger.error(f"Erro ao buscar itens do banco: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar itens do banco")
    finally:
        conn.close()

@router.get("/zabbix/db/item-info")
def get_item_info_from_db(item_id: int = Query(..., description="ID do item")):
    """
    Retorna informações detalhadas de um item específico.
    """
    query = """
        SELECT hostgroup_id, hostgroup_name, host_id, host_name, 
               item_id, item_name, graph_ids, graph_names, 
               trigger_ids, trigger_names
        FROM v_zabbix
        WHERE item_id = %s
        LIMIT 1
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (item_id,))
            result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Item não encontrado")
            
        return {"item_info": result}
    except Exception as e:
        logger.error(f"Erro ao buscar informações do item: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar informações do item")
    finally:
        conn.close()

@router.get("/zabbix/db/metrics-summary")
def get_metrics_summary_from_db(item_id: int = Query(..., description="ID do item")):
    """
    Retorna um resumo das métricas de um item (últimos valores, estatísticas, etc.).
    """
    query = """
        SELECT 
            COUNT(*) as total_records,
            MIN(clock) as first_record,
            MAX(clock) as last_record,
            AVG(CAST(value AS DECIMAL(10,2))) as avg_value,
            MIN(CAST(value AS DECIMAL(10,2))) as min_value,
            MAX(CAST(value AS DECIMAL(10,2))) as max_value
        FROM v_zabbix_metrics
        WHERE itemid = %s
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (item_id,))
            result = cursor.fetchone()
        
        return {"metrics_summary": result}
    except Exception as e:
        logger.error(f"Erro ao buscar resumo das métricas: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar resumo das métricas")
    finally:
        conn.close()

# Endpoint adicional para buscar itens com informações de métricas disponíveis
@router.get("/zabbix/db/items-with-metrics")
def get_items_with_metrics_from_db(host_id: int = Query(..., description="ID do host")):
    """
    Retorna os itens de um host que possuem métricas disponíveis na view v_zabbix_metrics.
    """
    query = """
        SELECT DISTINCT v.item_id, v.item_name, 
               COUNT(vm.itemid) as metrics_count,
               MAX(vm.clock) as last_metric_time
        FROM v_zabbix v
        LEFT JOIN v_zabbix_metrics vm ON v.item_id = vm.itemid
        WHERE v.host_id = %s
        GROUP BY v.item_id, v.item_name
        HAVING COUNT(vm.itemid) > 0
        ORDER BY v.item_name
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (host_id,))
            results = cursor.fetchall()
        return {"items": results}
    except Exception as e:
        logger.error(f"Erro ao buscar itens com métricas: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar itens com métricas")
    finally:
        conn.close()


@router.get("/zabbix/db/graph-to-item")
def get_item_id_from_graph_id(graph_id: int = Query(..., description="ID do gráfico")):
    """
    Retorna o item_id associado a um graph_id específico da view v_zabbix.
    """
    query = """
        SELECT item_id
        FROM v_zabbix
        WHERE FIND_IN_SET(%s, graph_ids) > 0
        LIMIT 1
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (graph_id,))
            result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Item ID não encontrado para o gráfico fornecido")
            
        return {"item_id": result["item_id"]}
    except Exception as e:
        logger.error(f"Erro ao buscar item_id para graph_id {graph_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar item_id para o gráfico")
    finally:
        conn.close()

@router.get("/zabbix/db/graph-items")
def get_items_by_graph(graph_id: int = Query(...)):
    """
    Retorna todos os itemids e nomes associados a um gráfico.
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
            return [{"itemid": r["itemid"], "name": r["item_name"]} for r in rows]
    except Exception as e:
        logger.error(f"Erro ao buscar itens do gráfico: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar itens do gráfico")
    finally:
        if conn:
            conn.close()


@router.post("/zabbix/db/report-metrics")
async def get_report_metrics(request: Request):
    """
    Recebe um JSON de configuração de relatório e devolve as métricas históricas
    para cada gráfico definido, pronto para o frontend gerar os gráficos.
    """
    try:
        payload = await request.json()
        hosts = payload.get("hosts", [])
        result = {}
        for host in hosts:
            host_id = host.get("id")
            host_name = host.get("name")
            result[host_id] = {"name": host_name, "graphs": {}}
            for graph in host.get("graphs", []):
                graph_id = graph["id"]
                from_time = graph["from_time"]
                to_time = graph["to_time"]
                # Busca todos os itemids associados a esse graph_id
                items = get_items_by_graph(int(graph_id))
                graph_data = []
                for item in items:
                    itemid = item["itemid"]
                    item_name = item["name"]
                    value_type = get_item_value_type(itemid)
                    if value_type in [0, 3]:  # Numéricos
                        data = get_item_metrics(itemid, from_time, to_time, limit=2000)
                        graph_data.append({
                            "itemid": itemid,
                            "item_name": item_name,
                            "data": data,
                            "type": "numeric"
                        })
                    else:  # Texto/log/str
                        last = get_last_value_of_item(itemid)
                        graph_data.append({
                            "itemid": itemid,
                            "item_name": item_name,
                            "last_value": last,
                            "type": "text"
                        })
                result[host_id]["graphs"][graph_id] = {
                    "name": graph["name"],
                    "data": graph_data
                }
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar métricas para relatório customizado: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar métricas para relatório")
