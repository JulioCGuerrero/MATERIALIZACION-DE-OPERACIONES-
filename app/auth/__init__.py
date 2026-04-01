"""Blueprint de autenticacion."""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# Import tardio para registrar rutas sin ciclos de import.
from app.auth import routes  # noqa: E402,F401
