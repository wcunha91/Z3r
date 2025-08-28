# app/zabbix/service.py

import requests
from app.core.logging import logger
from datetime import datetime, timezone, timedelta
from collections import Counter

from zoneinfo import ZoneInfo
ZABBIX_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class ZabbixService:

    @staticmethod
    def get_version(api_url: str) -> str:
        """Obtém a versão do Zabbix via API JSON-RPC."""
        payload = {
            "jsonrpc": "2.0",
            "method": "apiinfo.version",
            "params": {},
            "id": 1
        }
        try:
            logger.info(f"Detectando versão do Zabbix: {api_url}")
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            return response.json().get("result")
        except Exception as e:
            logger.error(f"Erro ao obter versão do Zabbix: {str(e)}")
            raise

    @staticmethod
    def authenticate_api(api_url: str, username: str, password: str) -> str:
        """Autentica via API JSON-RPC e retorna o token."""
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"username": username, "password": password},
            "id": 1
        }
        try:
            logger.info(f"Autenticando via API: {api_url} - usuário: {username}")
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "result" in data:
                logger.info(f"Token obtido com sucesso")
                return data["result"]
            raise Exception(data.get("error", {}).get("data", "Erro desconhecido"))
        except Exception as e:
            logger.error(f"Erro ao autenticar via API: {str(e)}")
            raise

    @staticmethod
    def authenticate_web(web_url: str, username: str, password: str) -> str:
        """Autentica na interface web do Zabbix e retorna o cookie zbx_session."""
        login_payload = {
            "name": username,
            "password": password,
            "autologin": 1,
            "enter": "Sign in"
        }
        try:
            logger.info(f"Autenticando via WEB: {web_url} - usuário: {username}")
            session = requests.Session()
            response = session.post(f"{web_url}/index.php", data=login_payload)
            if "zbx_session" in session.cookies:
                logger.info("Sessão Web autenticada com sucesso")
                return session.cookies["zbx_session"]
            raise Exception("zbx_session ausente (falha na autenticação WEB)")
        except Exception as e:
            logger.error(f"Erro ao autenticar via WEB: {str(e)}")
            raise

    @staticmethod
    def call_zabbix_api(api_url: str, method: str, params: dict, auth_token: str = None, version: str = "7.2") -> dict:
        """
        Chamada genérica à API do Zabbix.
        - Para versões < 7.2: usa campo "auth" no body
        - Para versões >= 7.2: usa Authorization: Bearer TOKEN no cabeçalho
        """
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }

        headers = {"Content-Type": "application/json"}

        if version >= "7.2":
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
        else:
            if auth_token:
                payload["auth"] = auth_token

        logger.info(f"Chamando método Zabbix: {method} - versão {version}")
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if "result" in data:
                return data["result"]
            raise Exception(data.get("error", {}).get("data", "Erro desconhecido"))
        except Exception as e:
            logger.error(f"Erro na chamada {method}: {str(e)}")
            raise

    @staticmethod
    def authenticate(api_url: str, web_url: str, username: str, password: str) -> dict:
        """
        Realiza autenticação API + Web e retorna token + cookie + versão.
        """
        logger.info("Iniciando autenticação unificada no Zabbix")

        version = ZabbixService.get_version(api_url)
        api_token = ZabbixService.authenticate_api(api_url, username, password)
        web_cookie = ZabbixService.authenticate_web(web_url, username, password)

        return {
            "version": version,
            "api_token": api_token,
            "web_cookie": web_cookie
        }


### Listar Hostgroup (GET http://127.0.0.1:8000/zabbix/hostgroups)
    @staticmethod
    def list_hostgroups(api_url: str, auth_token: str, version: str) -> list:
        """
        Retorna todos os hostgroups disponíveis no Zabbix.
        """
        return ZabbixService.call_zabbix_api(api_url, "hostgroup.get", {
            "output": ["groupid", "name"],
            "sortfield": "name"
        }, auth_token=auth_token, version=version)

### Listar Hosts por HostgroupID (GET http://127.0.0.1:8000/zabbix/hosts?group_id=5)
    @staticmethod
    def list_hosts_by_group(api_url: str, auth_token: str, version: str, group_id: str) -> list:
        """
        Lista os hosts vinculados a um determinado hostgroup.
        """
        return ZabbixService.call_zabbix_api(
            api_url=api_url,
            method="host.get",
            params={
                "output": ["hostid", "name", "status", "available"],
                "groupids": group_id,
                "sortfield": "name"
            },
            auth_token=auth_token,
            version=version
        )

### Listar Graphs por HostID (GET http://127.0.0.1:8000/zabbix/graphs?host_id=10532)
    @staticmethod
    def list_graphs_by_host(api_url: str, auth_token: str, version: str, host_id: str) -> list:
        """
        Retorna todos os gráficos associados a um host específico.
        """
        return ZabbixService.call_zabbix_api(
            api_url=api_url,
            method="graph.get",
            params={
                "output": ["graphid", "name", "width", "height", "graphtype"],
                "hostids": host_id,
                "sortfield": "name"
            },
            auth_token=auth_token,
            version=version
        )

###Obter Grafico
    @staticmethod
    def get_graph_image(
        web_url: str,
        auth_token: str,
        graph_id: str,
        from_time: str,
        to_time: str,
        width: int = 900,
        height: int = 200
    ) -> bytes:
        """
        Obtém a imagem de um gráfico via frontend Web do Zabbix.
        """
        chart_url = f"{web_url}/chart2.php"
        params = {
            "graphid": graph_id,
            "from": from_time,
            "to": to_time,
            "width": width,
            "height": height,
            "profileIdx": "web.charts.filter",
            "resolve_macros": 1
        }

        headers = {"Cookie": f"zbx_session={auth_token}"}

        logger.info(f"Buscando imagem do gráfico {graph_id} de {from_time} até {to_time}")
        try:
            response = requests.get(chart_url, params=params, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Erro ao obter imagem do gráfico: {str(e)}")
            raise


    @staticmethod
    def get_events_by_hosts(api_url, auth_token, host_ids, time_from, time_till):
        payload = {
            "jsonrpc": "2.0",
            "method": "event.get",
            "params": {
                "output": "extend",
                "hostids": host_ids,
                "time_from": time_from,   # ✅ Correto
                "time_till": time_till,   # ✅ Correto
                "value": [0, 1],          # OK e PROBLEM
                "object": 0,              # Trigger
                "sortfield": ["clock"],
                "sortorder": "ASC"
            },
            "auth": auth_token,
            "id": 1
        }

        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        return response.json().get("result", [])






    @staticmethod
    def count_incidents(api_url, auth_token, version, from_time, to_time, group_id=None):
        """Conta o número de incidentes (eventos de problema) em um período."""
        try:
            from_timestamp = int(datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S").timestamp())
            to_timestamp = int(datetime.strptime(to_time, "%Y-%m-%d %H:%M:%S").timestamp())
            params = {
                "source": 0,
                "object": 0,
                "time_from": from_timestamp,
                "time_till": to_timestamp,
                "value": 1,  # Apenas problemas
                "countOutput": True
            }
            if group_id:
                params["groupids"] = group_id

            logger.info(f"[Zabbix] Contando incidentes de {from_time} a {to_time}")
            return ZabbixService.call_zabbix_api(api_url, "event.get", params, auth_token, version)
        except Exception as e:
            logger.error(f"[Zabbix] Erro ao contar incidentes: {str(e)}")
            raise

    

    @staticmethod
    def list_top_triggers(api_url, auth_token, version, from_time, to_time, group_id=None, limit=5):
        """Lista as triggers mais ativadas em um período."""
        try:
            from_timestamp = int(datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S").timestamp())
            to_timestamp = int(datetime.strptime(to_time, "%Y-%m-%d %H:%M:%S").timestamp())

            params = {
                "source": 0,
                "object": 0,
                "time_from": from_timestamp,
                "time_till": to_timestamp,
                "value": 1,
                "output": ["objectid"]
            }
            if group_id:
                params["groupids"] = group_id

            logger.info(f"[Zabbix] Buscando eventos para top triggers de {from_time} a {to_time}")
            events = ZabbixService.call_zabbix_api(api_url, "event.get", params, auth_token, version)

            # Contar ativações por objectid
            counts = Counter(event["objectid"] for event in events)

            # Pegar os top N triggers
            top_trigger_ids = [trigger_id for trigger_id, _ in counts.most_common(limit)]
            if not top_trigger_ids:
                return []

            # Buscar detalhes das triggers
            triggers = ZabbixService.call_zabbix_api(api_url, "trigger.get", {
                "triggerids": top_trigger_ids,
                "output": ["triggerid", "description", "priority"],
                "selectHosts": ["hostid", "name"]
            }, auth_token, version)

            # Combinar contagem com detalhes
            result = []
            for trigger in triggers:
                result.append({
                    "triggerid": trigger["triggerid"],
                    "description": trigger["description"],
                    "priority": trigger["priority"],
                    "host": trigger.get("hosts", [{}])[0].get("name", ""),
                    "incident_count": counts.get(trigger["triggerid"], 0)
                })

            return result
        except Exception as e:
            logger.error(f"Erro ao listar top triggers: {str(e)}")
            raise

    @staticmethod
    def list_open_problems(
        api_url: str,
        auth_token: str,
        version: str,
        group_id: str = None
    ) -> list:
        """
        Lista os problemas em aberto.
        Parâmetros:
        - group_id: Filtra por hostgroup (opcional)
        """
        try:
            params = {
                "output": ["eventid", "name", "severity", "clock"],
                "selectAcknowledges": ["userid", "action", "message"],
                "selectTags": ["tag", "value"],
                "sortfield": "eventid",
                "sortorder": "DESC"
            }
            if group_id:
                params["groupids"] = group_id

            logger.info(f"Buscando problemas em aberto")
            return ZabbixService.call_zabbix_api(api_url, "problem.get", params, auth_token, version)
        except Exception as e:
            logger.error(f"Erro ao listar problemas em aberto: {str(e)}")
            raise
    
    @staticmethod
    def calculate_downtime(api_url, auth_token, version, from_time, to_time, trigger_id=None, group_id=None):
        """Calcula o tempo total de downtime com detalhes por intervalo."""
        try:
            # Converte períodos para timestamp UTC, considerando o fuso horário local
            from_dt = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZABBIX_TIMEZONE)
            to_dt = datetime.strptime(to_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZABBIX_TIMEZONE)
            from_ts = int(from_dt.timestamp())
            to_ts = int(to_dt.timestamp())

            # Monta parâmetros para event.get
            params = {
                "source": 0,
                "object": 0,
                "time_from": from_ts,
                "time_till": to_ts,
                "value": [0, 1],  # PROBLEM e RESOLVED
                "sortfield": "clock",
                "sortorder": "ASC",
                "output": ["eventid", "clock", "value", "objectid", "acknowledged", "severity"],
                "selectHosts": ["hostid", "name"],
                "selectTags": ["tag", "value"]
            }
            if trigger_id:
                params["objectids"] = [trigger_id]
            if group_id:
                params["groupids"] = [group_id]

            logger.info(f"[Zabbix] Buscando eventos para cálculo de downtime")
            events = ZabbixService.call_zabbix_api(api_url, "event.get", params, auth_token, version)

            if not events:
                return {"downtime_seconds": 0, "downtime_human": "0s", "intervals": []}

            # Coletar todos os trigger_ids únicos para buscar nomes depois
            trigger_ids = list({e["objectid"] for e in events})

            # Buscar detalhes das triggers
            triggers_info = {}
            if trigger_ids:
                trigger_details = ZabbixService.call_zabbix_api(api_url, "trigger.get", {
                    "triggerids": trigger_ids,
                    "output": ["triggerid", "description", "priority"],
                    "selectHosts": ["hostid", "name"]
                }, auth_token, version)

                for trig in trigger_details:
                    triggers_info[trig["triggerid"]] = {
                        "description": trig["description"],
                        "priority": trig["priority"]
                    }

            total_downtime = 0
            current_problem = None
            intervals = []

            for event in events:
                event_time = int(event["clock"])
                event_value = int(event["value"])  # 1 = PROBLEM, 0 = RESOLVED

                if event_value == 1 and current_problem is None:
                    current_problem = {
                        "start_ts": event_time,
                        "event_id_start": event["eventid"],
                        "trigger_id": event["objectid"],
                        "acknowledged": bool(event.get("acknowledged", 0)),
                        "severity": event.get("severity", "unknown"),
                        "tags": event.get("tags", []),
                        "host": event.get("hosts", [{}])[0].get("name", "Unknown"),
                        "trigger_name": triggers_info.get(event["objectid"], {}).get("description", "N/A"),
                        "trigger_priority": triggers_info.get(event["objectid"], {}).get("priority", "N/A")
                    }
                elif event_value == 0 and current_problem:
                    start_ts = max(current_problem["start_ts"], from_ts)
                    end_ts = min(event_time, to_ts)

                    if start_ts < end_ts:
                        downtime = end_ts - start_ts
                        total_downtime += downtime
                        intervals.append({
                            "start": datetime.fromtimestamp(start_ts, tz=timezone.utc).astimezone(ZABBIX_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                            "end": datetime.fromtimestamp(end_ts, tz=timezone.utc).astimezone(ZABBIX_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                            "duration_seconds": downtime,
                            "event_id_start": current_problem["event_id_start"],
                            "event_id_end": event["eventid"],
                            "trigger_id": current_problem["trigger_id"],
                            "trigger_name": current_problem["trigger_name"],
                            "trigger_priority": current_problem["trigger_priority"],
                            "host": current_problem["host"],
                            "severity": current_problem["severity"],
                            "acknowledged": current_problem["acknowledged"],
                            "tags": current_problem["tags"]
                        })
                    current_problem = None

            # Se ainda houver PROBLEM aberto no final do período
            if current_problem:
                start_ts = max(current_problem["start_ts"], from_ts)
                end_ts = to_ts
                if start_ts < end_ts:
                    downtime = end_ts - start_ts
                    total_downtime += downtime
                    intervals.append({
                        "start": datetime.fromtimestamp(start_ts, tz=timezone.utc).astimezone(ZABBIX_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                        "end": datetime.fromtimestamp(end_ts, tz=timezone.utc).astimezone(ZABBIX_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                        "duration_seconds": downtime,
                        "event_id_start": current_problem["event_id_start"],
                        "event_id_end": None,
                        "trigger_id": current_problem["trigger_id"],
                        "trigger_name": current_problem["trigger_name"],
                        "trigger_priority": current_problem["trigger_priority"],
                        "host": current_problem["host"],
                        "severity": current_problem["severity"],
                        "acknowledged": current_problem["acknowledged"],
                        "tags": current_problem["tags"]
                    })

            return {
                "downtime_seconds": total_downtime,
                "downtime_human": str(timedelta(seconds=total_downtime)),
                "intervals": intervals
            }
        except Exception as e:
            logger.error(f"[Zabbix] Erro ao calcular downtime: {str(e)}")
            raise

