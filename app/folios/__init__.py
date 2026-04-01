"""Blueprint de folios."""

from flask import Blueprint

folios_bp = Blueprint("folios", __name__)

# Import tardio para registrar rutas sin ciclos de import.
from app.folios import routes  # noqa: E402,F401
