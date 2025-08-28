# app/auth/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import re

import bcrypt
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .settings import JWT_SECRET, JWT_EXPIRES_MINUTES

bearer_scheme = HTTPBearer(auto_error=False)

def _dt_now():
    return datetime.now(timezone.utc)

def create_access_token(claims: Dict[str, Any], expires_minutes: int = JWT_EXPIRES_MINUTES) -> str:
    to_encode = claims.copy()
    exp = _dt_now() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": exp, "iat": _dt_now()})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

def verify_password(input_password: str, stored_password: str) -> bool:
    """
    Aceita:
    - senha em texto puro no .env
    - hash bcrypt no formato 'bcrypt:<hash>'
    """
    if stored_password.startswith("bcrypt:"):
        hashed = stored_password.split("bcrypt:", 1)[1].encode()
        return bcrypt.checkpw(input_password.encode(), hashed)
    return input_password == stored_password

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais ausentes")
    payload = decode_token(credentials.credentials)
    return payload.get("user")  # dict com dados do usuário
