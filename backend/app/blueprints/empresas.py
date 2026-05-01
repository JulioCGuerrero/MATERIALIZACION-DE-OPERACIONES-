from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Empresa
from ..services.auditoria import log_event

empresas_bp = Blueprint("empresas", __name__)


def _empresa_dict(e: Empresa) -> dict:
    return {
        "id": e.id,
        "nombre": e.nombre,
        "rfc": e.rfc,
        "activo": e.activo,
        "creado_en": e.creado_en.isoformat() if e.creado_en else None,
    }


@empresas_bp.get("/empresas")
def listar_empresas():
    items = Empresa.query.order_by(Empresa.nombre.asc()).all()
    return jsonify([_empresa_dict(e) for e in items])


@empresas_bp.post("/empresas")
def crear_empresa():
    body = request.get_json(silent=True) or {}
    required = ["nombre", "rfc"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    empresa = Empresa(
        nombre=body["nombre"].strip(),
        rfc=body["rfc"].strip().upper(),
        activo=bool(body.get("activo", True)),
    )
    db.session.add(empresa)
    db.session.flush()
    log_event("empresas", empresa.id, "crear", {"rfc": empresa.rfc}, body.get("usuario"))
    db.session.commit()
    return jsonify(_empresa_dict(empresa)), 201
