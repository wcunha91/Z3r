# app/auth/proxy_guard.py
import os
from fastapi import Header, HTTPException, status

DEV_MODE = os.getenv("ENV", "").lower() in {"dev", "development"} or os.getenv("DEV_MODE", "false").lower() == "true"

async def require_internal_proxy(x_internal_proxy: str | None = Header(None)):
    # Em DEV, permitimos chamadas sem o header
    if DEV_MODE:
        return
    # Em produção, o header é obrigatório
    if x_internal_proxy != "1":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
