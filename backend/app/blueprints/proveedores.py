from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Expediente, Proveedor
from ..services.auditoria import log_event
from ..services.clasificador import clasificar_proveedor
from ..services.serializers import expediente_to_dict

proveedores_bp = Blueprint("proveedores", __name__)


def _proveedor_dict(p: Proveedor) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "rfc": p.rfc,
        "tipo": p.tipo,
        "nivel": p.nivel,
        "banco": p.banco,
        "cuenta": p.cuenta,
        "clabe": p.clabe,
        "repse": p.repse,
        "tiene_fisico": p.tiene_fisico,
        "efos_ok": p.efos_ok,
        "activo": p.activo,
        "creado_en": p.creado_en.isoformat() if p.creado_en else None,
    }


@proveedores_bp.get("/proveedores")
def listar_proveedores():
    items = Proveedor.query.order_by(Proveedor.nombre.asc()).all()
    return jsonify([_proveedor_dict(p) for p in items])


@proveedores_bp.get("/proveedores/<int:proveedor_id>")
def obtener_proveedor(proveedor_id: int):
    p = Proveedor.query.get_or_404(proveedor_id)
    return jsonify(_proveedor_dict(p))


@proveedores_bp.post("/proveedores")
def crear_proveedor():
    body = request.get_json(silent=True) or {}
    required = ["nombre", "rfc", "tipo", "monto", "repse", "tiene_fisico"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    clasificado = clasificar_proveedor(
        tipo=body["tipo"],
        monto=float(body["monto"]),
        repse=bool(body["repse"]),
        tiene_fisico=bool(body["tiene_fisico"]),
    )

    proveedor = Proveedor(
        nombre=body["nombre"],
        rfc=body["rfc"],
        tipo=body["tipo"],
        nivel=clasificado["nivel"],
        banco=body.get("banco"),
        cuenta=body.get("cuenta"),
        clabe=body.get("clabe"),
        repse=bool(body["repse"]),
        tiene_fisico=bool(body["tiene_fisico"]),
        efos_ok=bool(body.get("efos_ok", True)),
        activo=bool(body.get("activo", True)),
    )
    db.session.add(proveedor)
    db.session.flush()
    log_event("proveedores", proveedor.id, "crear", {"nivel": proveedor.nivel}, body.get("usuario"))
    db.session.commit()

    return jsonify({**_proveedor_dict(proveedor), "clasificacion": clasificado}), 201


@proveedores_bp.patch("/proveedores/<int:proveedor_id>")
def actualizar_proveedor(proveedor_id: int):
    p = Proveedor.query.get_or_404(proveedor_id)
    body = request.get_json(silent=True) or {}

    for field in ["nombre", "rfc", "tipo", "banco", "cuenta", "clabe"]:
        if field in body:
            setattr(p, field, body[field])

    for field in ["repse", "tiene_fisico", "efos_ok", "activo"]:
        if field in body:
            setattr(p, field, bool(body[field]))

    if any(k in body for k in ["tipo", "monto", "repse", "tiene_fisico"]):
        monto = float(body.get("monto", 0))
        clasificado = clasificar_proveedor(p.tipo, monto, p.repse, p.tiene_fisico)
        p.nivel = clasificado["nivel"]

    log_event("proveedores", p.id, "actualizar", body, body.get("usuario"))
    db.session.commit()
    return jsonify(_proveedor_dict(p))


@proveedores_bp.get("/proveedores/<int:proveedor_id>/expedientes")
def expedientes_proveedor(proveedor_id: int):
    Proveedor.query.get_or_404(proveedor_id)
    expedientes = (
        Expediente.query.join(Expediente.folio)
        .filter_by(proveedor_id=proveedor_id)
        .order_by(Expediente.id.desc())
        .all()
    )
    return jsonify([expediente_to_dict(e) for e in expedientes])
