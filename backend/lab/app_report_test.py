import streamlit as st
import requests
import json

# Config
BACKEND_URL = "http://127.0.0.1:8000/zabbix/db/report-metrics"

st.set_page_config("Validador de Relatório Zabbix", layout="centered")

st.title("Validador de Relatório - Athena Reports")

st.markdown("""
Faça upload do arquivo JSON de configuração do relatório para buscar as métricas direto do banco.
""")

uploaded = st.file_uploader("Upload do arquivo .json", type=["json"])

if uploaded:
    try:
        config = json.load(uploaded)
        st.success("Arquivo carregado!")
        st.json(config)
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {str(e)}")
        st.stop()

    if st.button("Enviar e Buscar Métricas"):
        with st.spinner("Buscando dados no backend..."):
            try:
                resp = requests.post(BACKEND_URL, json=config, timeout=60)
                if resp.status_code == 200:
                    dados = resp.json()
                    st.success("Dados recebidos do backend!")
                    st.write("Resumo da resposta:")
                    st.json(dados)
                    # Exemplo: Mostrar gráfico simples para cada host/grafico se houver dados
                    for host in dados.get("hosts", []):
                        st.subheader(f"Host: {host['name']}")
                        for graph in host.get("graphs_data", []):
                            st.markdown(f"**Gráfico:** {graph.get('name')}")
                            # Se vier um array de pontos para plotagem:
                            values = graph.get("metrics")
                            if values and isinstance(values, list) and len(values) > 1:
                                import pandas as pd
                                df = pd.DataFrame(values)
                                if "clock" in df.columns and "value" in df.columns:
                                    df["clock"] = pd.to_datetime(df["clock"])
                                    st.line_chart(df.set_index("clock")["value"])
                            else:
                                st.write("Sem dados numéricos para plotar.")
                else:
                    st.error(f"Erro do backend: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Falha na requisição: {e}")
