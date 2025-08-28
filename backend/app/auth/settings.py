# app/auth/settings.py
import os

SIMPLE_AUTH_USER = os.getenv("SIMPLE_AUTH_USER", "admin")
SIMPLE_AUTH_PASSWORD = os.getenv("SIMPLE_AUTH_PASSWORD", "admin123")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "43200"))  # 30 dias
