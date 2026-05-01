from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Folio, Traspaso
from ..services.auditoria import log_event
from ..services.bloqueo import puede_pagar

traspasos_bp = Blueprint("traspasos", __name__)


@traspasos_bp.get("/traspasos")
def listar_traspasos():
    q = Traspaso.query
    if request.args.get("folio_id"):
        q = q.filter(Traspaso.folio_id == int(request.args["folio_id"]))
    if request.args.get("estado"):
        q = q.filter(Traspaso.estado == request.args["estado"])
    if request.args.get("empresa_id"):
        q = q.join(Traspaso.folio).filter(Folio.empresa_id == int(request.args["empresa_id"]))

    items = q.order_by(Traspaso.creado_en.desc()).all()
    return jsonify([
        {
            "id": t.id,
            "folio_id": t.folio_id,
            "folio_numero": t.folio.numero,
            "proveedor": t.folio.proveedor.nombre,
            "empresa_id": t.folio.empresa.id if t.folio.empresa else None,
            "empresa": t.folio.empresa.nombre if t.folio.empresa else None,
            "folio_bancario": t.folio_bancario,
            "monto": t.monto,
            "fecha": t.fecha,
            "estado": t.estado,
            "excede_presup": t.excede_presup,
            "diferencia": t.diferencia,
        }
        for t in items
    ])


@traspasos_bp.get("/traspasos/<int:traspaso_id>")
def detalle_traspaso(traspaso_id: int):
    t = Traspaso.query.get_or_404(traspaso_id)
    return jsonify(
        {
            "id": t.id,
            "folio_id": t.folio_id,
            "folio_numero": t.folio.numero,
            "proveedor": t.folio.proveedor.nombre,
            "empresa_id": t.folio.empresa.id if t.folio.empresa else None,
            "empresa": t.folio.empresa.nombre if t.folio.empresa else None,
            "folio_bancario": t.folio_bancario,
            "banco_origen": t.banco_origen,
            "banco_destino": t.banco_destino,
            "cuenta_destino": t.cuenta_destino,
            "monto": t.monto,
            "fecha": t.fecha,
            "estado": t.estado,
            "excede_presup": t.excede_presup,
            "diferencia": t.diferencia,
            "registrado_por": t.registrado_por,
        }
    )


@traspasos_bp.post("/traspasos")
def crear_traspaso():
    body = request.get_json(silent=True) or {}
    required = ["folio_id", "monto", "banco_origen", "fecha"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    folio = Folio.query.get_or_404(int(body["folio_id"]))
    if not folio.expediente:
        return jsonify({"error": "Folio sin expediente"}), 400

    pago = puede_pagar(folio.expediente.id)
    if not pago["puede_pagar"]:
        return jsonify(
            {
                "error": "Pago bloqueado por materialidad incompleta",
                "detalle": pago,
            }
        ), 403

    monto = float(body["monto"])
    excede_presup = monto > folio.presupuesto
    diferencia = round(monto - folio.presupuesto, 2) if excede_presup else 0.0
    estado = body.get("estado") or ("alerta" if excede_presup else "pendiente")

    traspaso = Traspaso(
        folio_id=folio.id,
        folio_bancario=body.get("folio_bancario"),
        banco_origen=body["banco_origen"],
        banco_destino=body.get("banco_destino"),
        cuenta_destino=body.get("cuenta_destino"),
        monto=monto,
        fecha=body["fecha"],
        estado=estado,
        excede_presup=excede_presup,
        diferencia=diferencia,
        registrado_por=body.get("registrado_por"),
    )

    db.session.add(traspaso)
    db.session.flush()
    log_event("traspasos", traspaso.id, "crear", {"monto": monto, "folio": folio.numero}, body.get("registrado_por"))
    if excede_presup:
        log_event(
            "traspasos",
            traspaso.id,
            "alerta_ia",
            {"mensaje": "Monto excede presupuesto", "diferencia": diferencia},
            body.get("registrado_por"),
        )

    db.session.commit()

    return jsonify({"id": traspaso.id, "estado": estado, "excede_presup": excede_presup, "diferencia": diferencia}), 201
