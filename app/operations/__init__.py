from flask import Blueprint

operations_bp = Blueprint("operations", __name__)

from app.operations import routes  # noqa: E402,F401
