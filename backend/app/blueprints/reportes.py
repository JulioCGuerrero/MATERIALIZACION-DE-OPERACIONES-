from flask import Blueprint, jsonify, request

from ..services.reportes import (
    reporte_por_nivel_data,
    reporte_semaforo_data,
    reporte_trazabilidad_data,
)

reportes_bp = Blueprint("reportes", __name__)


@reportes_bp.get("/reportes/nivel")
def reporte_por_nivel():
    nivel = request.args.get("nivel", type=int)
    empresa_id = request.args.get("empresa_id", type=int)
    return jsonify(reporte_por_nivel_data(nivel, empresa_id))


@reportes_bp.get("/reportes/semaforo")
def reporte_semaforo():
    return jsonify(reporte_semaforo_data())


@reportes_bp.get("/reportes/trazabilidad")
def reporte_trazabilidad():
    empresa_id = request.args.get("empresa_id", type=int)
    return jsonify(reporte_trazabilidad_data(empresa_id))
