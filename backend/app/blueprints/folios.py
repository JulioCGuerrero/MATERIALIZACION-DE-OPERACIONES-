from datetime import datetime

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Documento, Expediente, Folio, Proveedor
from ..services.auditoria import log_event
from ..services.bloqueo import calcular_completitud
from ..services.catalogo import DOCS_BY_LEVEL

folios_bp = Blueprint("folios", __name__)


def _folio_dict(folio: Folio) -> dict:
    exp = folio.expediente
    return {
        "id": folio.id,
        "numero": folio.numero,
        "proveedor_id": folio.proveedor_id,
        "proveedor_nombre": folio.proveedor.nombre,
        "nivel": folio.proveedor.nivel,
        "presupuesto": folio.presupuesto,
        "periodo": folio.periodo,
        "estado": folio.estado,
        "completitud": exp.completitud if exp else 0.0,
        "pago_bloqueado": exp.pago_bloqueado if exp else True,
    }


@folios_bp.get("/folios")
def listar_folios():
    q = Folio.query
    if request.args.get("periodo"):
        q = q.filter(Folio.periodo == request.args["periodo"])
    if request.args.get("estado"):
        q = q.filter(Folio.estado == request.args["estado"])
    if request.args.get("proveedor_id"):
        q = q.filter(Folio.proveedor_id == int(request.args["proveedor_id"]))

    folios = q.order_by(Folio.creado_en.desc()).all()
    return jsonify([_folio_dict(f) for f in folios])


@folios_bp.get("/folios/<int:folio_id>")
def detalle_folio(folio_id: int):
    f = Folio.query.get_or_404(folio_id)
    data = _folio_dict(f)
    if f.expediente:
        data["expediente_id"] = f.expediente.id
        data["documentos"] = [
            {
                "id": d.id,
                "tipo": d.tipo,
                "subido": d.subido,
            }
            for d in f.expediente.documentos
        ]
    return jsonify(data)


@folios_bp.post("/folios")
def crear_folio():
    body = request.get_json(silent=True) or {}
    required = ["numero", "proveedor_id", "presupuesto", "periodo"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    proveedor = Proveedor.query.get_or_404(int(body["proveedor_id"]))
    folio = Folio(
        numero=body["numero"],
        proveedor_id=proveedor.id,
        presupuesto=float(body["presupuesto"]),
        periodo=body["periodo"],
        estado=body.get("estado", "activo"),
    )
    db.session.add(folio)
    db.session.flush()

    expediente = Expediente(folio_id=folio.id, completitud=0.0, pago_bloqueado=True)
    db.session.add(expediente)
    db.session.flush()

    for tipo_doc in DOCS_BY_LEVEL[proveedor.nivel]:
        db.session.add(Documento(expediente_id=expediente.id, tipo=tipo_doc, subido=False))

    log_event("folios", folio.id, "crear", {"proveedor_id": proveedor.id}, body.get("usuario"))
    db.session.commit()
    calcular_completitud(expediente.id)

    return jsonify(_folio_dict(folio)), 201


@folios_bp.patch("/folios/<int:folio_id>")
def actualizar_folio(folio_id: int):
    folio = Folio.query.get_or_404(folio_id)
    body = request.get_json(silent=True) or {}

    if "estado" in body:
        folio.estado = body["estado"]
        if body["estado"] == "cerrado":
            folio.cerrado_en = datetime.utcnow()

    log_event("folios", folio.id, "actualizar", body, body.get("usuario"))
    db.session.commit()
    return jsonify(_folio_dict(folio))
