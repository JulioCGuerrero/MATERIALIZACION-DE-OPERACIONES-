"""Blueprint del modulo operativo (SAT, CFDI, conciliacion, etc.)."""

from flask import Blueprint

operations_bp = Blueprint("operations", __name__)

# Import tardio para registrar rutas sin ciclos de import.
from app.operations import routes  # noqa: E402,F401
