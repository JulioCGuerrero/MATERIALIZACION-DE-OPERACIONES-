from datetime import datetime

from flask import Blueprint, jsonify, request

from ..services.automation import ejecutar_automatizacion
from ..models import Empresa

automation_bp = Blueprint("automation", __name__)


@automation_bp.post("/automatizacion/ejecutar")
def ejecutar():
    body = request.get_json(silent=True) or {}
    periodo = body.get("periodo")
    usuario = body.get("usuario", "sistema_auto")
    result = ejecutar_automatizacion(periodo=periodo, usuario=usuario)
    return jsonify(result)


@automation_bp.get("/automatizacion/estado")
def estado():
    periodo = request.args.get("periodo") or datetime.now().strftime("%Y-%m")
    empresas_activas = Empresa.query.filter_by(activo=True).count()
    return jsonify(
        {
            "periodo_objetivo": periodo,
            "empresas_activas": empresas_activas,
            "siguiente_paso": "Ejecutar POST /api/automatizacion/ejecutar para crear ciclos y alertas",
        }
    )
