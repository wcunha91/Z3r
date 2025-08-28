# app/glpi/db_service.py

import pymysql
from app.core.config import MYSQL_HOSTGLPI, MYSQL_USERGLPI, MYSQL_PASSGLPI, MYSQL_DBGLPI
from app.core.logging import logger


def get_glpi_db_connection():
    """Cria conexão com o banco de dados MySQL do GLPI."""
    try:
        return pymysql.connect(
            host=MYSQL_HOSTGLPI,
            user=MYSQL_USERGLPI,
            password=MYSQL_PASSGLPI,
            database=MYSQL_DBGLPI,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        logger.error(f"[GLPI] Erro ao conectar no banco: {str(e)}")
        raise
