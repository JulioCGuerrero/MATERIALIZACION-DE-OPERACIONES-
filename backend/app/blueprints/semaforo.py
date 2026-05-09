from flask import Blueprint, jsonify, request

from ..models import Proveedor
from ..services.semaforo import calcular_semaforo

semaforo_bp = Blueprint("semaforo", __name__)


@semaforo_bp.get("/semaforo")
def semaforo_total():
    empresa_id = request.args.get("empresa_id", type=int)
    proveedor_id = request.args.get("proveedor_id", type=int)
    nivel = request.args.get("nivel", type=int)
    return jsonify(calcular_semaforo(empresa_id=empresa_id, proveedor_id=proveedor_id, nivel=nivel))


@semaforo_bp.get("/semaforo/efos")
def semaforo_efos():
    total = Proveedor.query.filter_by(activo=True).count()
    ok = Proveedor.query.filter_by(activo=True, efos_ok=True).count()
    estado = "verde" if total == ok else "rojo"
    return jsonify(
        {
            "estado": estado,
            "valor": f"{ok}/{total} proveedores OK",
            "ley": "Art. 69-B CFF",
        }
    )
