import os
from pathlib import Path

from sqlalchemy.engine import URL

DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()


class Config:
    BASE_DIR = Path(__file__).resolve().parents[2]
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or (
        URL.create(
            "postgresql+psycopg2",
            username=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASS"),
            database=os.environ.get("DB_NAME", "postgres"),
            query={"host": f"/cloudsql/{os.environ['INSTANCE_CONNECTION_NAME']}"},
        )
        if os.environ.get("INSTANCE_CONNECTION_NAME")
        else f"sqlite:///{BASE_DIR / 'database.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        **(
            {"connect_args": {"options": "-csearch_path=materializacion_operaciones"}}
            if DATABASE_URL or os.environ.get("INSTANCE_CONNECTION_NAME")
            else {}
        ),
    }
    JSON_SORT_KEYS = False
    AUTO_CREATE_SCHEMA = os.environ.get("AUTO_CREATE_SCHEMA", "").lower() in {"1", "true", "yes"}
    STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "25")) * 1024 * 1024
    SECRET_KEY = (os.environ.get("SECRET_KEY") or "local-development-only").strip()
    AUTH_TOKEN_MAX_AGE = int(os.environ.get("AUTH_TOKEN_MAX_AGE", "28800"))
    ALLOW_LEGACY_AUTH_HEADERS = os.environ.get("ALLOW_LEGACY_AUTH_HEADERS", "").lower() in {"1", "true", "yes"}
