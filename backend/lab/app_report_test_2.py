import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="Validador de Endpoint de Métricas Zabbix", layout="wide")
st.title("Validador de Endpoint de Métricas Zabbix")

uploaded_file = st.file_uploader("Envie o arquivo de configuração do relatório (.json)", type="json")

if uploaded_file:
    config = json.load(uploaded_file)
    st.write("Configuração recebida:", config)
    backend_url = st.text_input("URL do backend", "http://127.0.0.1:8000/zabbix/db/report-metrics")

    if st.button("Buscar métricas e gerar gráficos"):
        with st.spinner("Consultando backend e montando gráficos..."):
            resp = requests.post(backend_url, json=config)
            if resp.status_code != 200:
                st.error(f"Erro: {resp.status_code}\n{resp.text}")
            else:
                data = resp.json()
                st.success("Dados recebidos do backend!")
                st.write("Resumo da resposta:", data)

                for host_id, host_data in data.items():
                    st.header(f"Host: {host_data.get('name', host_id)}")
                    graphs = host_data.get("graphs", {})
                    for graph_id, graph_info in graphs.items():
                        st.subheader(f"Gráfico: {graph_info.get('name', graph_id)}")
                        series_list = graph_info.get("data", [])
                        # Para cada série de dados dentro do gráfico
                        for serie in series_list:
                            st.write(f"Item: {serie.get('item_name')} ({serie.get('itemid')})")
                            data_points = serie.get("data", [])
                            # Só faz gráfico se tiver dados e se for numérico
                            if serie.get("type", "numeric") == "numeric" and data_points:
                                df = pd.DataFrame(data_points)
                                if "data_coleta" in df.columns and "value" in df.columns:
                                    df["data_coleta"] = pd.to_datetime(df["data_coleta"])
                                    st.line_chart(df.set_index("data_coleta")["value"])
                                else:
                                    st.write(df)
                            else:
                                # Exibe texto, status, etc.
                                if data_points:
                                    st.write("Último valor:", data_points[-1])
                                else:
                                    st.write("Sem dados.")



st.markdown("---")
st.caption("Desenvolvido para validação rápida dos endpoints de relatório do Zabbix.")
