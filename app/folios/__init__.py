from flask import Blueprint

folios_bp = Blueprint("folios", __name__)

from app.folios import routes  # noqa: E402,F401
