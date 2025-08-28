# app/auth/routes.py
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.logging import logger
from .schemas import LoginIn, LoginOut, MeOut, UserOut
from .settings import SIMPLE_AUTH_USER, SIMPLE_AUTH_PASSWORD
from .security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginOut)
def simple_login(body: LoginIn):
    identifier = body.identifier.strip().lower()
    if identifier != SIMPLE_AUTH_USER.lower():
        logger.warning(f"[AUTH] Login falhou: user não confere ({identifier})")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")

    if not verify_password(body.password, SIMPLE_AUTH_PASSWORD):
        logger.warning("[AUTH] Login falhou: senha inválida")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")

    user = UserOut(
        id="fixed-1",
        username=SIMPLE_AUTH_USER,
        name=SIMPLE_AUTH_USER,
        role="admin",
        must_change_password=False,
    )
    token = create_access_token({"user": user.model_dump()})
    logger.info(f"[AUTH] Login OK para {SIMPLE_AUTH_USER}")
    return LoginOut(access_token=token, user=user)

@router.get("/me", response_model=MeOut)
def me(user=Depends(get_current_user)):
    return user
