import os
from pathlib import Path

from sqlalchemy.engine import URL


class Config:
    BASE_DIR = Path(__file__).resolve().parents[2]
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
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
    JSON_SORT_KEYS = False
    AUTO_CREATE_SCHEMA = os.environ.get("AUTO_CREATE_SCHEMA", "").lower() in {"1", "true", "yes"}
