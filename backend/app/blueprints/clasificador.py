from flask import Blueprint, jsonify, request

from ..services.clasificador import clasificar_proveedor

clasificador_bp = Blueprint("clasificador", __name__)


@clasificador_bp.post("/clasificar")
def clasificar():
    body = request.get_json(silent=True) or {}
    required = ["tipo", "monto", "repse", "tiene_fisico"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    result = clasificar_proveedor(
        tipo=body["tipo"],
        monto=float(body["monto"]),
        repse=bool(body["repse"]),
        tiene_fisico=bool(body["tiene_fisico"]),
        tipo_empresa=(body.get("tipo_empresa") or "servicios"),
        empresa_id=body.get("empresa_id"),
        usuario=body.get("usuario"),
        save_evaluation=bool(body.get("guardar_evaluacion", False)),
    )
    return jsonify(result)
