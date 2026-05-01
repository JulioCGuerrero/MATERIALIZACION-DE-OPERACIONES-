from flask import Blueprint, jsonify, request

from ..services.kpis import kpis_personal_data

kpis_bp = Blueprint("kpis", __name__)


@kpis_bp.get("/kpis/personal")
def kpis_personal():
    periodo = request.args.get("periodo")
    return jsonify(kpis_personal_data(periodo))
