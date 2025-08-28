# app/auth/schemas.py
from pydantic import BaseModel

class LoginIn(BaseModel):
    identifier: str  # email ou usuário
    password: str

class UserOut(BaseModel):
    id: str
    username: str
    name: str
    role: str = "admin"
    must_change_password: bool = False

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class MeOut(UserOut):
    pass
