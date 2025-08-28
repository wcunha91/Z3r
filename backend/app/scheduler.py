#athena-reports/app/scheduler.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apscheduler.schedulers.background import BackgroundScheduler
from app.reports.service import ReportService
from app.core.logging import logger

def run_daily_reports():
    logger.info("Executando relatório DIÁRIO pelo scheduler")
    ReportService.executar_relatorios_agendados("daily")

def run_weekly_reports():
    logger.info("Executando relatório SEMANAL pelo scheduler")
    ReportService.executar_relatorios_agendados("weekly")

def run_monthly_reports():
    logger.info("Executando relatório MENSAL pelo scheduler")
    ReportService.executar_relatorios_agendados("monthly")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    
    # Para teste (intervalos curtos, pode aumentar conforme necessidade)
    #scheduler.add_job(run_daily_reports, 'interval', seconds=10, id='daily_report_test')
    #scheduler.add_job(run_weekly_reports, 'interval', seconds=30, id='weekly_report_test')
    #scheduler.add_job(run_monthly_reports, 'interval', seconds=60, id='monthly_report_test')

    # Para produção:
    scheduler.add_job(run_daily_reports, 'cron', hour=7, minute=0, id='daily_report')
    scheduler.add_job(run_weekly_reports, 'cron', day_of_week='mon', hour=12, minute=53, id='weekly_report')
    scheduler.add_job(run_monthly_reports, 'cron', day=1, hour=11, id='monthly_report')

    scheduler.start()
    logger.info("Scheduler APScheduler iniciado.")
    return scheduler  # <-- Retorna o objeto para controle futuro

# Não coloque laço infinito aqui!
