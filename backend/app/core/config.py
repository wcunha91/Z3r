# app/core/config.py

import os
from dotenv import load_dotenv

load_dotenv()

ZABBIX_API_URL = os.getenv("ZABBIX_API_URL")
ZABBIX_WEB_URL = os.getenv("ZABBIX_WEB_URL")
ZABBIX_USER = os.getenv("ZABBIX_USER")
ZABBIX_PASS = os.getenv("ZABBIX_PASS")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASS = os.getenv("MYSQL_PASS")
MYSQL_DB   = os.getenv("MYSQL_DB")

MYSQL_HOSTGLPI = os.getenv("MYSQL_HOSTGLPI")
MYSQL_USERGLPI = os.getenv("MYSQL_USERGLPI")
MYSQL_PASSGLPI = os.getenv("MYSQL_PASSGLPI")
MYSQL_DBGLPI   = os.getenv("MYSQL_DBGLPI")
