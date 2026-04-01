import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///servicia.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Batia")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
