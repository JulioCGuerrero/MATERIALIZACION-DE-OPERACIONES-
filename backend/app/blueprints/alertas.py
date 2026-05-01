from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Alerta
from ..services.alertas import generar_alertas

alertas_bp = Blueprint("alertas", __name__)


def _alerta_dict(a: Alerta) -> dict:
    return {
        "id": a.id,
        "tipo": a.tipo,
        "severidad": a.severidad,
        "mensaje": a.mensaje,
        "estado": a.estado,
        "origen": a.origen,
        "proveedor_id": a.proveedor_id,
        "empresa_id": a.empresa_id,
        "folio_id": a.folio_id,
        "expediente_id": a.expediente_id,
        "periodo": a.periodo,
        "creado_en": a.creado_en.isoformat() if a.creado_en else None,
    }


@alertas_bp.get("/alertas")
def listar_alertas():
    q = Alerta.query
    if request.args.get("estado"):
        q = q.filter(Alerta.estado == request.args["estado"])
    if request.args.get("proveedor_id"):
        q = q.filter(Alerta.proveedor_id == int(request.args["proveedor_id"]))
    if request.args.get("empresa_id"):
        q = q.filter(Alerta.empresa_id == int(request.args["empresa_id"]))
    if request.args.get("periodo"):
        q = q.filter(Alerta.periodo == request.args["periodo"])
    items = q.order_by(Alerta.creado_en.desc()).all()
    return jsonify([_alerta_dict(x) for x in items])


@alertas_bp.post("/alertas/generar")
def generar_alertas_endpoint():
    body = request.get_json(silent=True) or {}
    result = generar_alertas(body.get("periodo"))
    return jsonify(result)


@alertas_bp.patch("/alertas/<int:alerta_id>/resolver")
def resolver_alerta(alerta_id: int):
    a = Alerta.query.get_or_404(alerta_id)
    a.estado = "resuelta"
    db.session.commit()
    return jsonify(_alerta_dict(a))
