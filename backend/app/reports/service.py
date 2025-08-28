import os
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import json

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, FrameBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from PIL import Image as PILImage

import plotly.graph_objs as go


# === ADICIONAR estes imports no topo do arquivo (junto dos demais) ===
from app.configs.routes import CONFIG_DIR  # diretório das configs .json dos relatórios agendados
from app.mail.service import send_report_email_sync  # envio síncrono p/ usar dentro do scheduler

# === ADICIONAR estes imports no topo do arquivo (junto dos demais) ===
from app.configs.routes import CONFIG_DIR  # diretório das configs .json dos relatórios agendados
from app.mail.service import send_report_email_sync  # envio síncrono p/ usar dentro do scheduler



# ==== Simulação dos módulos externos ====
try:
    from app.zabbix.db_service import get_items_by_graph, get_item_metrics
    from app.core.logging import logger
    from app.glpi.services import (
        get_tempo_chamados, get_chamados_bi, get_usuarios_entidade,
        get_evolutivo, get_evolutivo_tratados, processar_metrica_chamados
    )
except ImportError:
    print("AVISO: Módulos 'app.*' não encontrados. Usando stubs para demonstração.")
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    logger = MockLogger()
    import numpy as np
    def get_items_by_graph(graph_id):
        return [{"itemid": f"10{graph_id}", "item_name": "Interface X: Bits received"}, {"itemid": f"20{graph_id}", "item_name": "Interface X: Bits sent"}]
    def get_item_metrics(itemid, from_time, to_time):
        start_date = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(to_time, "%Y-%m-%d %H:%M:%S")
        num_points = 250
        time_delta = (end_date - start_date) / num_points
        base_value = 150 * 1024 * 1024 if "received" in itemid else 80 * 1024 * 1024
        return [{"data_coleta": start_date + i * time_delta, "value": base_value + np.sin(i / 20.0) * (base_value/4) + np.random.rand() * (base_value/10)} for i in range(num_points)]
    def get_tempo_chamados(entidade_id, inicio, fim):
        return [
            {"id_chamado": 1234, "titulo": "Problema de conexão com a VPN", "status": 2, "requerente": "Bruno Di Giacomo", "data_abertura": datetime(2025, 7, 10, 10, 30)},
            {"id_chamado": 1235, "titulo": "Computador lento", "status": 6, "requerente": "Marina Matsuyama", "data_abertura": datetime(2025, 7, 15, 14, 0)},
            {"id_chamado": 1236, "titulo": "Acesso a sistema", "status": 5, "requerente": "Bruno Di Giacomo", "data_abertura": datetime(2025, 7, 20, 9, 0)},
            {"id_chamado": 1237, "titulo": "Instalar programa", "status": 2, "requerente": "Suporte Clooud", "data_abertura": datetime(2025, 7, 25, 11, 0)},
        ]
    def get_chamados_bi(entidade_id, inicio, fim):
        return [
            {"status": "Aguardando Cliente"},
            {"status": "Fechado"},
            {"status": "Fechado"},
            {"status": "Fechado"},
            {"status": "Fechado"},
            {"status": "Fechado"},
            {"status": "Fechado"},
            {"status": "Fechado"},
        ]
    def get_usuarios_entidade(entidade_id):
        return [
            {"nome": "Bruno Di Giacomo", "login": "bgiacomo@blackbirdco.com.br", "email": "bgiacomo@blackbirdco.com.br"},
            {"nome": "Suporte Clooud", "login": "suporte@clooud.com.br", "email": "suporte@clooud.com.br"},
            {"nome": "Marina Matsuyama", "login": "mmatsuyama@blackbirdco.com.br", "email": "mmatsuyama@blackbirdco.com.br"},
        ]
    def get_evolutivo(entidade_id, meses=6): return []
    def get_evolutivo_tratados(entidade_id, meses=6): return [{"mes": "Mar 2025", "qtd": 6}, {"mes": "Apr 2025", "qtd": 3}, {"mes": "May 2025", "qtd": 5}, {"mes": "Jun 2025", "qtd": 6}, {"mes": "Jul 2025", "qtd": 6}]
    def processar_metrica_chamados(lista):
        return {
            "total": 8,
            "status": {"Aguardando Cliente": 1, "Fechado": 7},
            "categorias": [("Firewall > VPN", 5), ("Endpoint", 1), ("Wireless", 1)]
        }

PDF_COLORS = [
    "#0D47A1", "#FF8A65", "#00B8D4", "#2E7D32", "#8E24AA",
    "#D81B60", "#FFD600", "#F44336", "#43A047", "#0288D1", "#F9A825",
]
BG_COLOR = "#FFFFFF"
TITLE_COLOR = "#212121"
LABEL_COLOR = "#424242"
FOOTER_COLOR = "#BDBDBD"
COVER_BG = "#f0f2f5"
ATHENA_LOGO_PATH = "app/static/athena_logo.png"

if not os.path.exists(ATHENA_LOGO_PATH):
    os.makedirs(os.path.dirname(ATHENA_LOGO_PATH), exist_ok=True)
    PILImage.new('RGB', (200, 60), color='#0D47A1').save(ATHENA_LOGO_PATH)

def get_logo_path(logo_filename=None):
    default_logo = "app/static/logo.png"
    if logo_filename:
        possible_logo = os.path.join("configs/logos", logo_filename)
        if os.path.exists(possible_logo): return possible_logo
    if not os.path.exists(default_logo):
        os.makedirs(os.path.dirname(default_logo), exist_ok=True)
        PILImage.new('RGB', (200, 60), color='grey').save(default_logo)
    return default_logo

def format_bytes(value, pos=None):
    if value == 0: return '0'
    units = ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps']
    value_bits = value * 8
    power = 1000
    i = 0
    while value_bits >= power and i < len(units) - 1:
        value_bits /= power
        i += 1
    return f"{value_bits:.1f} {units[i]}"

def downsample_timeseries(times, values, target_points=500):
    n = len(values)
    if n <= target_points: return times, values
    import numpy as np
    idx = np.linspace(0, n - 1, target_points).astype(int)
    return [times[i] for i in idx], [values[i] for i in idx]


def _first_week_of_month(dt: datetime) -> bool:
    """True se a data estiver entre os 7 primeiros dias do mês."""
    return 1 <= dt.day <= 7

def _month_range(year: int, month: int):
    """Retorna (inicio_date, fim_date) do mês (datetime.date)."""
    last_day = monthrange(year, month)[1]
    inicio = datetime(year, month, 1).date()
    fim = datetime(year, month, last_day).date()
    return inicio, fim

def _prev_month_range(ref: datetime):
    """Retorna (inicio_date, fim_date) do mês anterior ao ref (ambos datetime.date)."""
    first_this = ref.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    return _month_range(last_prev.year, last_prev.month)

def _compute_glpi_period(frequency: str, start_date: datetime, end_date: datetime, today: datetime) -> tuple:
    """
    Define (inicio_date, fim_date) para GLPI:
      - monthly: mês anterior inteiro
      - weekly:
          * se start_date está na 1ª semana do mês atual -> mês anterior inteiro
          * senão -> a própria semana [start_date, end_date]
      - fallback: usa [start_date, end_date]
    """
    if frequency == "monthly":
        return _prev_month_range(today)
    if frequency == "weekly":
        if _first_week_of_month(start_date):
            return _prev_month_range(today)
        return start_date.date(), end_date.date()
    return start_date.date(), end_date.date()

def _inject_glpi_period(cfg: dict, start_date: datetime, end_date: datetime, today: datetime) -> dict:
    """
    Se existir cfg['glpi'] com 'entidade_id', injeta 'inicio'/'fim' automaticamente.
    Nunca apagamos `entidade_id`. Retorna o próprio dict (mutável).
    """
    glpi = cfg.get("glpi")
    if not isinstance(glpi, dict):
        return cfg
    if not glpi.get("entidade_id"):
        return cfg

    frequency = cfg.get("frequency")
    inicio_date, fim_date = _compute_glpi_period(frequency, start_date, end_date, today)
    glpi["inicio"] = inicio_date.isoformat()  # YYYY-MM-DD
    glpi["fim"] = fim_date.isoformat()        # YYYY-MM-DD
    cfg["glpi"] = glpi
    return cfg



class ReportService:
    @staticmethod
    def _setup_styles():
        styles = getSampleStyleSheet()
        styles['Normal'].fontSize = 10
        styles['Normal'].textColor = '#333333'
        styles['Normal'].fontName = "Helvetica"
        styles.add(ParagraphStyle(name="CoverTitle", fontSize=36, alignment=0, textColor="#0D47A1", fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="CoverSubtitle", fontSize=20, alignment=0, textColor=TITLE_COLOR, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="CoverInfo", fontSize=12, alignment=0, textColor=LABEL_COLOR, fontName="Helvetica"))
        styles.add(ParagraphStyle(name="PageTitle", fontSize=22, spaceAfter=15, textColor="#0D47A1", fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="SectionTitle", fontSize=16, spaceBefore=18, spaceAfter=8, textColor=TITLE_COLOR, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="GraphTitle", fontSize=12, spaceAfter=4, textColor="#333333", fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="ErrorText", fontSize=10, textColor=colors.red, leftIndent=20))
        styles.add(ParagraphStyle(name="InfoText", fontSize=11, leading=15, textColor=LABEL_COLOR, fontName="Helvetica"))
        styles.add(ParagraphStyle(name="GlpiTableHeader", fontSize=10, fontName="Helvetica-Bold", textColor=TITLE_COLOR, alignment=1, backColor="#f5f5f5"))
        styles.add(ParagraphStyle(name="GlpiTableCell", fontSize=9, fontName="Helvetica", textColor=LABEL_COLOR, alignment=0))
        styles.add(ParagraphStyle(name="FooterText", fontSize=9, fontName="Helvetica", textColor=FOOTER_COLOR, alignment=1))
        return styles

    @staticmethod
    def _plot_evolutivo_tratados_barras(evolutivo_data):
        meses = [item['mes'] for item in evolutivo_data]
        quantidades = [item['qtd'] for item in evolutivo_data]
        fig = go.Figure(data=[go.Bar(x=meses, y=quantidades, marker_color='#0D47A1')])
        fig.update_layout(
            title_text="Evolutivo de Chamados Tratados",
            xaxis_title="Mês",
            yaxis_title="Quantidade",
            font=dict(family='Helvetica', size=10, color='#333'),
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=BG_COLOR,
        )
        buf = BytesIO()
        fig.write_image(buf, format="png", width=500, height=300, scale=1.5)
        buf.seek(0)
        return buf

    @staticmethod
    def _plot_graph_plotly(items, graph_data):
        fig = go.Figure()
        has_data = False
        for item_idx, item in enumerate(items):
            metrics = get_item_metrics(item["itemid"], graph_data['from_time'], graph_data['to_time'])
            if metrics and "value" in metrics[0]:
                times = [d["data_coleta"] for d in metrics][::-1]
                values = [float(d["value"]) for d in metrics][::-1]
                t, v = downsample_timeseries(times, values)
                if v:
                    min_val = min(v)
                    max_val = max(v)
                    min_idx = v.index(min_val)
                    max_idx = v.index(max_val)
                    fig.add_trace(go.Scatter(
                        x=[t[min_idx]], y=[min_val], mode='markers+text',
                        marker=dict(size=12, color="#00C853", symbol='circle'),
                        text=[f"Min: {format_bytes(min_val)}"], textposition='bottom center',
                        name=f"Min ({item['item_name']})",
                        showlegend=False
                    ))
                    fig.add_trace(go.Scatter(
                        x=[t[max_idx]], y=[max_val], mode='markers+text',
                        marker=dict(size=12, color="#D50000", symbol='circle'),
                        text=[f"Max: {format_bytes(max_val)}"], textposition='top center',
                        name=f"Max ({item['item_name']})",
                        showlegend=False
                    ))
                fig.add_trace(go.Scatter(
                    x=t, y=v, mode='lines',
                    name=item["item_name"],
                    line=dict(width=2, color=PDF_COLORS[item_idx % len(PDF_COLORS)])
                ))
                has_data = True
        if not has_data:
            return None
        fig.update_layout(
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=BG_COLOR,
            margin=dict(l=30, r=30, t=40, b=40),
            xaxis_title='Horário',
            yaxis_title='Valor',
            legend=dict(x=1.01, y=1, borderwidth=0, bgcolor='rgba(255,255,255,0.7)'),
            font=dict(family='Helvetica', size=10, color='#333'),
            shapes=[
                dict(type="rect",
                    xref="paper", yref="paper",
                    x0=0, y0=0, x1=1, y1=1,
                    line=dict(color="rgba(0,0,0,0.08)", width=1),
                    fillcolor="rgba(0,0,0,0.03)",
                    layer="below")
            ]
        )
        if any('bit' in item['item_name'].lower() or 'traffic' in item['item_name'].lower() for item in items):
            fig.update_yaxes(tickformat=".2s", title_text="Tráfego (bits/s)")
        fig.update_xaxes(tickformat="%d/%m %H:%M")
        buf = BytesIO()
        fig.write_image(buf, format="png", width=900, height=350, scale=1.5)
        buf.seek(0)
        return buf

    @staticmethod
    def generate_pdf_db(data, config_file: Path = None):
        if hasattr(data, 'dict'): data = data.dict()
        hosts = data.get('hosts', [])
        summary_data = data.get('summary', None)
        glpi_info = data.get("glpi", None)
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_hostgroup = data.get('hostgroup', {}).get('name', 'report').replace(" ", "_").replace("/", "_")
        file_path = f"reports/relatorio_{sanitized_hostgroup}_{timestamp}.pdf"
        styles = ReportService._setup_styles()
        elements = []

        # CAPA
        elements.append(PageBreak())
        # GLPI (antes dos gráficos)
        if glpi_info:
            glpi_data = ReportService._buscar_dados_glpi_local(glpi_info)
            if glpi_data:
                ReportService._add_glpi_section(elements, styles, glpi_data)
            else:
                elements.append(Paragraph("Erro ao coletar dados do Service Desk/GLPI.", styles["ErrorText"]))
                elements.append(PageBreak())
        # CONTEÚDO DE GRÁFICOS (sem sumário e sem quebra desnecessária)
        ReportService._add_content_pages(elements, styles, hosts)

        doc = SimpleDocTemplate(file_path, pagesize=A4, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
        doc.build(
            elements,
            onFirstPage=lambda c, d: ReportService._draw_cover_layout(c, d, data, styles),
            onLaterPages=ReportService._draw_page_layout
        )
        logger.info(f"Relatório DB salvo em: {file_path}")
        return file_path

    @staticmethod
    def _draw_cover_layout(canvas, doc, data, styles):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(COVER_BG))
        canvas.rect(0, 0, A4[0], A4[1], fill=1)
        canvas.setFillColor(colors.HexColor("#bbdefb"))
        canvas.setStrokeColor(colors.HexColor("#bbdefb"))
        canvas.line(0, A4[1] * 0.7, A4[0], A4[1] * 0.9)
        canvas.line(0, A4[1] * 0.5, A4[0], A4[1] * 0.6)
        canvas.line(A4[0] * 0.5, 0, A4[0] * 0.7, A4[1])
        canvas.setFillColor(colors.HexColor("#e3f2fd"))
        canvas.setStrokeColor(colors.HexColor("#e3f2fd"))
        canvas.line(A4[0] * 0.2, 0, A4[0] * 0.4, A4[1])
        canvas.drawImage(ATHENA_LOGO_PATH, inch, A4[1] - 1.5 * inch, width=2.5*inch, height=0.8*inch, preserveAspectRatio=True,mask='auto')
        client_logo_path = get_logo_path(data.get('logo_filename'))
        if os.path.exists(client_logo_path):
            canvas.drawImage(client_logo_path, A4[0] - inch - 2.5*inch, inch, width=2.5*inch, height=0.8*inch, preserveAspectRatio=True,mask='auto')
        else:
            canvas.setFillColor(colors.HexColor("#bdbdbd"))
            canvas.rect(A4[0] - inch - 2.5*inch, inch, 2.5*inch, 0.8*inch, fill=1)
            canvas.setFillColor(colors.black)
            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawCentredString(A4[0] - inch - 1.25*inch, inch + 0.3*inch, "CLIENT LOGO")
        canvas.setFillColor(colors.HexColor("#0D47A1"))
        canvas.setFont("Helvetica-Bold", 36)
        canvas.drawString(inch, A4[1] * 0.6, "Athena Reports")
        canvas.setFillColor(colors.HexColor("#212121"))
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(inch, A4[1] * 0.55, "Relatório Mensal de Performance")
        canvas.setFont("Helvetica", 12)
        canvas.drawString(inch, A4[1] * 0.52, f"{datetime.now().strftime('%B %Y')}")
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.HexColor("#424242"))
        y_pos = 4 * inch
        #canvas.drawString(inch, y_pos, "Software sob medida, resultados que você confia")
        min_date, max_date = ReportService._find_min_max_dates(data.get('hosts', []))
        info_data = [
            ["Período de Análise:", f"{min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}"],
            ["Data de Geração:", datetime.now().strftime('%d/%m/%Y %H:%M:%S')],
            ["Analista Responsável:", data.get('analyst', 'N/A')]
        ]
        y_table_start = A4[1] * 0.4
        for label, value in info_data:
            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawString(inch, y_table_start, label)
            canvas.setFont("Helvetica", 10)
            canvas.drawString(inch + 1.8 * inch, y_table_start, value)
            y_table_start -= 0.3 * inch
        canvas.restoreState()

    @staticmethod
    def _draw_page_layout(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, A4[0], A4[1], fill=1)
        canvas.drawImage(ATHENA_LOGO_PATH, inch, A4[1] - 0.75 * inch, height=0.5 * inch, preserveAspectRatio=True)
        canvas.setStrokeColor("#e0e0e0")
        canvas.line(inch, A4[1] - 1.0 * inch, A4[0] - inch, A4[1] - 1.0 * inch)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(inch, 0.6 * inch, "Relatório de Monitoramento")
        canvas.drawRightString(A4[0] - inch, 0.6 * inch, f"Página {doc.page - 1}")
        canvas.restoreState()

    @staticmethod
    def _add_content_pages(elements, styles, hosts):
        for i, host in enumerate(hosts, 1):
            elements.append(Paragraph(f"Host: {host.get('name', 'N/A')}", styles["PageTitle"]))
            elements.append(Spacer(1, 0.1 * inch))
            for j, graph_data in enumerate(host.get('graphs', []), 1):
                graph_elements = []
                graph_elements.append(Paragraph(f"{graph_data.get('name', 'N/A')}", styles["GraphTitle"]))
                try:
                    items = get_items_by_graph(int(graph_data['id']))
                    if not items:
                        graph_elements.append(Paragraph("Nenhum item encontrado para este gráfico.", styles["ErrorText"]))
                    else:
                        buf = ReportService._plot_graph_plotly(items, graph_data)
                        if buf:
                            graph_elements.append(Image(buf, width=7*inch, height=2.8*inch))
                        else:
                            graph_elements.append(Paragraph("Não há dados para exibir neste gráfico.", styles["ErrorText"]))
                except Exception as e:
                    logger.error(f"Falha ao gerar gráfico para '{graph_data.get('name')}': {e}")
                    graph_elements.append(Paragraph(f"Erro ao gerar gráfico: {e}", styles["ErrorText"]))
                elements.extend(graph_elements)
                elements.append(Spacer(1, 0.3 * inch))
            # Não faz PageBreak após cada host ou gráfico!

    @staticmethod
    def _buscar_dados_glpi_local(glpi_info):
        try:
            entidade_id = glpi_info["entidade_id"]
            inicio = glpi_info["inicio"]
            fim = glpi_info["fim"]
            tempos = get_tempo_chamados(entidade_id, inicio, fim)
            tratados = get_chamados_bi(entidade_id, inicio, fim)
            usuarios = get_usuarios_entidade(entidade_id)
            evolutivo_tratados = get_evolutivo_tratados(entidade_id)
            metricas = processar_metrica_chamados(tratados)
            logger.info(f"[GLPI] Dados coletados localmente para entidade {entidade_id}")
            return {
                "entidade_id": entidade_id,
                "periodo": {"inicio": inicio, "fim": fim},
                "chamados_detalhados": tempos,
                "usuarios": usuarios,
                "evolutivo_tratados": evolutivo_tratados,
                "metricas": metricas
            }
        except Exception as e:
            logger.error(f"Erro ao buscar dados locais do GLPI: {e}")
            return None

    @staticmethod
    def _add_glpi_section(elements, styles, glpi_data):
        elements.append(Paragraph("Service Desk - Relatório GLPI", styles["PageTitle"]))
        elements.append(Spacer(1, 0.15 * inch))
        metricas = glpi_data.get("metricas", {})
        if metricas:
            total_chamados = metricas.get("total", "-")
            elements.append(Paragraph(f"<b>Chamados Tratados: {total_chamados}</b>", styles["SectionTitle"]))
            elements.append(Spacer(1, 0.1 * inch))
            status_data = metricas.get("status", {})
            status_str = ", ".join([f"{k}: {v}" for k, v in status_data.items()])
            elements.append(Paragraph(f"<b>Chamados por Status:</b> {status_str}", styles["InfoText"]))
            elements.append(Spacer(1, 0.1 * inch))
            requerentes = {}
            for chamado in glpi_data.get("chamados_detalhados", []):
                requerente = chamado.get("requerente", "Desconhecido")
                requerentes[requerente] = requerentes.get(requerente, 0) + 1
            if requerentes:
                max_requerente = max(requerentes, key=requerentes.get)
                elements.append(Paragraph(f"<b>Quem mais abriu chamados:</b> {max_requerente} ({requerentes[max_requerente]} chamados)", styles["InfoText"]))
                elements.append(Spacer(1, 0.1 * inch))
            categorias = metricas.get("categorias", [])
            if categorias:
                principais_categorias = ", ".join([f"{cat[0]}: {cat[1]}" for cat in categorias[:3]])
                elements.append(Paragraph(f"<b>Principais Categorias:</b> {principais_categorias}", styles["InfoText"]))
                elements.append(Spacer(1, 0.3 * inch))
        evolutivo_tratados = glpi_data.get("evolutivo_tratados", [])
        if evolutivo_tratados:
            evolutivo_buf = ReportService._plot_evolutivo_tratados_barras(evolutivo_tratados)
            #elements.append(Paragraph("<b>Evolutivo de Chamados Tratados por Mês</b>", styles["SectionTitle"]))
            elements.append(Image(evolutivo_buf, width=8*inch, height=4*inch))
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(PageBreak())

        usuarios = glpi_data.get("usuarios", [])
        if usuarios:
            usuarios_elements = []
            usuarios_elements.append(Paragraph("<b>Pessoas Autorizadas para Solicitações</b>", styles["SectionTitle"]))
            usuarios_data = [["Nome", "Login", "E-mail"]]
            for u in usuarios:
                usuarios_data.append([
                    Paragraph(u.get("nome", ""), styles["GlpiTableCell"]),
                    Paragraph(u.get("login", ""), styles["GlpiTableCell"]),
                    Paragraph(u.get("email", ""), styles["GlpiTableCell"])
                ])
            usuarios_table = Table(usuarios_data, colWidths=[2*inch, 1.3*inch, 2.3*inch])
            usuarios_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f5f5f5")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.extend(usuarios_elements)
            elements.append(usuarios_table)
            elements.append(Spacer(1, 0.3 * inch))
        chamados = glpi_data.get("chamados_detalhados", [])
        em_tratativas = [ch for ch in chamados if ch.get("status") not in [5, 6]]
        if em_tratativas:
            elements.append(Paragraph("<b>Chamados em Tratativas</b>", styles["SectionTitle"]))
            header = ["ID", "Título", "Status", "Abertura"]
            status_map = {1: "Novo", 2: "Em andamento", 3: "Pendente", 4: "Aguardando aprovação", 5: "Resolvido", 6: "Fechado"}
            tratativas_data = [header]
            for ch in em_tratativas:
                data_abertura = ch.get("data_abertura", "")
                if isinstance(data_abertura, datetime):
                    data_abertura = data_abertura.strftime("%Y-%m-%d %H:%M")
                elif data_abertura:
                    data_abertura = str(data_abertura)[:16]
                tratativas_data.append([
                    Paragraph(str(ch.get("id_chamado", "")), styles["GlpiTableCell"]),
                    Paragraph(ch.get("titulo", ""), styles["GlpiTableCell"]),
                    Paragraph(status_map.get(ch.get("status"), str(ch.get("status"))), styles["GlpiTableCell"]),
                    Paragraph(data_abertura, styles["GlpiTableCell"]),
                ])
            tratativas_table = Table(tratativas_data, colWidths=[1*inch, 3*inch, 1.5*inch, 1.5*inch])
            tratativas_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f5f5f5")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(tratativas_table)
        else:
            elements.append(Paragraph("<b>Chamados em Tratativas</b>", styles["SectionTitle"]))
            elements.append(Paragraph("Não foram registrados incidentes no ambiente durante este período. Nossa equipe permanece à disposição para qualquer necessidade futura.", styles["InfoText"]))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(PageBreak())


    @staticmethod
    def _find_min_max_dates(hosts):
        all_from, all_to = [], []
        for h in hosts:
            for g in h.get('graphs', []):
                try:
                    all_from.append(datetime.strptime(g['from_time'], "%Y-%m-%d %H:%M:%S"))
                    all_to.append(datetime.strptime(g['to_time'], "%Y-%m-%d %H:%M:%S"))
                except (ValueError, KeyError): continue
        return (min(all_from), max(all_to)) if all_from and all_to else (datetime.now(), datetime.now())

    @staticmethod
    def executar_relatorios_agendados(frequency: str, force: bool = False) -> list:
        """
        Executa relatórios agendados lendo os arquivos JSON em CONFIG_DIR.
        - Filtra por 'frequency' (weekly/monthly).
        - Atualiza período dos gráficos conforme a frequência.
        - Injeta período GLPI automaticamente (mês anterior na 1ª semana semanal, etc.).
        - Gera o PDF e envia por e-mail de forma síncrona (send_report_email_sync).
        - Atualiza 'last_sent_period' e 'last_sent' no JSON para evitar reenvios.
        Retorna uma lista de dicts com o resultado por arquivo processado.
        """
        processed = []
        try:
            config_files = sorted(CONFIG_DIR.glob("*.json"))
            logger.info(f"[SCHED] Executando agendados: {frequency} | arquivos={len(config_files)} | force={force}")

            today = datetime.now()

            for config_file in config_files:
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        cfg = json.load(f)

                    cfg_frequency = cfg.get("frequency")
                    emails = cfg.get("emails", [])

                    # Apenas os configs com a mesma frequência e com e-mails
                    if cfg_frequency != frequency or not emails:
                        continue

                    # Define período base (como no endpoint)
                    if frequency == "monthly":
                        # Mês anterior completo
                        start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                        end_date = today.replace(day=1) - timedelta(days=1)
                        period_str = start_date.strftime("%Y-%m")
                    elif frequency == "weekly":
                        # Semana anterior (segunda a domingo) relativa à data de hoje
                        start_date = today - timedelta(days=today.weekday() + 7)
                        end_date = start_date + timedelta(days=6)
                        period_str = start_date.strftime("%Y-%W")
                    else:
                        logger.warning(f"[SCHED] Frequência desconhecida em {config_file.name}")
                        continue

                    # Evita reenvio do mesmo período (a menos que force=True)
                    last_sent_period = cfg.get("last_sent_period")
                    if not force and last_sent_period == period_str:
                        logger.info(f"[SCHED] IGNORADO: {config_file.name} já enviado para {period_str}.")
                        continue

                    # Atualiza período dos gráficos
                    for host in cfg.get("hosts", []):
                        for graph in host.get("graphs", []):
                            graph["from_time"] = start_date.strftime("%Y-%m-%d 00:00:00")
                            graph["to_time"] = end_date.strftime("%Y-%m-%d 23:59:59")

                    # GLPI: injeta período automaticamente
                    cfg = _inject_glpi_period(cfg, start_date, end_date, today)

                    # Gera PDF
                    try:
                        file_path = ReportService.generate_pdf_db(cfg, config_file=config_file)
                    except Exception as e_gen:
                        logger.error(f"[SCHED] Falha ao gerar PDF ({config_file.name}): {e_gen}")
                        continue

                    # Envia e-mail síncrono (dentro do job)
                    try:
                        periodo = f"{start_date.date()} a {end_date.date()}"
                        logo_path = get_logo_path(cfg.get("logo_filename"))
                        send_report_email_sync(
                            recipients=emails,
                            file_path=file_path,
                            hostgroup_name=cfg.get("hostgroup", {}).get("name"),
                            periodo=periodo,
                            analyst=cfg.get("analyst"),
                            comments=cfg.get("comments"),
                            logo_path=logo_path
                        )
                        logger.info(f"[SCHED] Enviado: {config_file.name} -> {', '.join(emails)}")
                    except Exception as e_mail:
                        logger.error(f"[SCHED] Falha ao enviar e-mail ({config_file.name}): {e_mail}")
                        continue

                    # Atualiza controle no arquivo
                    cfg["last_sent_period"] = period_str
                    cfg["last_sent"] = datetime.now().isoformat()
                    try:
                        with open(config_file, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, indent=2, ensure_ascii=False)
                    except Exception as e_write:
                        logger.error(f"[SCHED] Falha ao salvar estado em {config_file.name}: {e_write}")

                    processed.append({
                        "filename": config_file.name,
                        "report_file": file_path,
                        "emails_sent": emails,
                        "last_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "period": period_str,
                        "force": force
                    })

                except Exception as e_cfg:
                    logger.error(f"[SCHED] Erro no processamento de {config_file.name}: {e_cfg}")
                    continue

            if not processed:
                logger.info(f"[SCHED] Nenhum relatório processado para frequency={frequency}.")
            else:
                logger.info(f"[SCHED] Total processados: {len(processed)} para frequency={frequency}")

            return processed

        except Exception as e:
            logger.error(f"[SCHED] Erro geral em executar_relatorios_agendados: {e}")
            return processed
