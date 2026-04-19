from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parents[2]
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'database.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
