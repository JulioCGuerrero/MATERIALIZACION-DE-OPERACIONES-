"""Configuracion central de la aplicacion.

Todas las variables se leen desde entorno (.env) para evitar hardcodear
secretos y facilitar mover el proyecto entre maquinas/entornos.
"""

import os
from dotenv import load_dotenv

# Carga variables de .env al entorno actual del proceso.
load_dotenv()


class Config:
    """Valores de configuracion por defecto.

    Si no existe una variable en entorno, se usa el valor fallback.
    """

    # Claves de seguridad para cookies/sesion y JWT.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    # Si no se define JWT_SECRET_KEY, reutiliza SECRET_KEY para no romper despliegues simples.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

    # Conexion a BD (SQLite por defecto).
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///servicia.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Branding mostrada en vistas.
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Batia")

    # Carpeta para evidencias subidas por usuario.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))

    # Limite maximo por request (archivos/form-data) en bytes: 16 MB.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
