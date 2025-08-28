# app/core/logging.py
# ------------------------------------------------------------
# Logging diário com arquivo nomeado por data:
#   logs/athena-YYYY-MM-DD.log
#
# - Roda em qualquer ambiente. O diretório base vem de app.core.paths.LOGS_DIR.
# - Rotaciona automaticamente à meia-noite (na primeira emissão do dia).
# - Retenção configurável via LOG_MAX_DAYS (dias). Padrão: 30.
# - Formato configurável via LOG_DATE_FMT. Padrão: %Y-%m-%d.
# - Prefixo do arquivo via LOG_FILE_PREFIX. Padrão: "athena".
# ------------------------------------------------------------

import logging
from pathlib import Path
from datetime import datetime, timedelta
import os

from app.core.paths import LOGS_DIR

LOG_PREFIX   = os.getenv("LOG_FILE_PREFIX", "athena")
LOG_DATE_FMT = os.getenv("LOG_DATE_FMT", "%Y-%m-%d")
LOG_MAX_DAYS = int(os.getenv("LOG_MAX_DAYS", "30"))

class DailyDateFileHandler(logging.FileHandler):
    """
    FileHandler que escreve sempre no arquivo do dia:
      <prefix>-YYYY-MM-DD.log
    Ao detectar a virada de dia, fecha o arquivo e abre um novo automaticamente.
    Também realiza limpeza de arquivos antigos conforme LOG_MAX_DAYS.
    """
    def __init__(self, logs_dir: Path, prefix: str = "athena", date_fmt: str = "%Y-%m-%d", encoding: str = "utf-8"):
        self.logs_dir = Path(logs_dir)
        self.prefix   = prefix
        self.date_fmt = date_fmt
        self.current_date = datetime.now().strftime(self.date_fmt)

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        filename = self._build_filename(self.current_date)
        super().__init__(filename, encoding=encoding)

        # Limpeza inicial (não bloqueante)
        self._cleanup_old_logs()

    def _build_filename(self, date_str: str) -> str:
        return str(self.logs_dir / f"{self.prefix}-{date_str}.log")

    def emit(self, record: logging.LogRecord) -> None:
        # Se mudamos de dia, troca o arquivo
        date_now = datetime.now().strftime(self.date_fmt)
        if date_now != self.current_date:
            self.acquire()
            try:
                self.close()
                self.current_date = date_now
                self.baseFilename = self._build_filename(self.current_date)
                self.stream = self._open()
                self._cleanup_old_logs()
            finally:
                self.release()
        super().emit(record)

    def _cleanup_old_logs(self) -> None:
        if LOG_MAX_DAYS <= 0:
            return
        cutoff = datetime.now() - timedelta(days=LOG_MAX_DAYS)
        try:
            pattern = f"{self.prefix}-*.log"
            for f in self.logs_dir.glob(pattern):
                try:
                    # extrai a parte da data
                    date_part = f.stem.replace(f"{self.prefix}-", "", 1)
                    dt = datetime.strptime(date_part, self.date_fmt)
                    if dt < cutoff:
                        f.unlink(missing_ok=True)
                except Exception:
                    # ignora arquivos fora do padrão
                    continue
        except Exception:
            # limpeza é best-effort; nunca deve derrubar a aplicação
            pass

# ---------- Configuração base do logging ----------
LOG_HANDLER = DailyDateFileHandler(LOGS_DIR, prefix=LOG_PREFIX, date_fmt=LOG_DATE_FMT)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    handlers=[LOG_HANDLER],
)

# Para logar: from app.core.logging import logger
logger = logging.getLogger("z3report")
