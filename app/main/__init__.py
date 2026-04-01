"""Blueprint de vistas principales (landing/dashboard)."""

from flask import Blueprint

main_bp = Blueprint("main", __name__)

# Import tardio para registrar rutas sin ciclos de import.
from app.main import routes  # noqa: E402,F401
