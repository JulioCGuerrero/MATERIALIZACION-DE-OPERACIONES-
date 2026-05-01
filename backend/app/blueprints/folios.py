from calendar import monthrange
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Documento, Empresa, Expediente, Folio, Proveedor
from ..services.auditoria import log_event
from ..services.bloqueo import calcular_completitud
from ..services.catalogo import DOCS_BY_LEVEL

folios_bp = Blueprint("folios", __name__)


def _fecha_limite_por_periodo(periodo: str) -> date:
    year, month = [int(x) for x in periodo.split("-")]
    return date(year, month, monthrange(year, month)[1])


def _folio_dict(folio: Folio) -> dict:
    exp = folio.expediente
    empresa = folio.empresa
    return {
        "id": folio.id,
        "numero": folio.numero,
        "proveedor_id": folio.proveedor_id,
        "proveedor_nombre": folio.proveedor.nombre,
        "empresa_id": empresa.id if empresa else None,
        "empresa_nombre": empresa.nombre if empresa else None,
        "nivel": folio.proveedor.nivel,
        "presupuesto": folio.presupuesto,
        "periodo": folio.periodo,
        "fecha_limite_entrega": folio.fecha_limite_entrega.isoformat() if folio.fecha_limite_entrega else None,
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
    if request.args.get("empresa_id"):
        q = q.filter(Folio.empresa_id == int(request.args["empresa_id"]))

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
    required = ["numero", "proveedor_id", "presupuesto", "periodo", "empresa_id"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    proveedor = Proveedor.query.get_or_404(int(body["proveedor_id"]))
    empresa = Empresa.query.get_or_404(int(body["empresa_id"]))
    folio = Folio(
        numero=body["numero"],
        proveedor_id=proveedor.id,
        empresa_id=empresa.id,
        presupuesto=float(body["presupuesto"]),
        periodo=body["periodo"],
        fecha_limite_entrega=(
            datetime.strptime(body["fecha_limite_entrega"], "%Y-%m-%d").date()
            if body.get("fecha_limite_entrega")
            else _fecha_limite_por_periodo(body["periodo"])
        ),
        estado=body.get("estado", "activo"),
    )
    db.session.add(folio)
    db.session.flush()

    expediente = Expediente(folio_id=folio.id, completitud=0.0, pago_bloqueado=True)
    db.session.add(expediente)
    db.session.flush()

    for tipo_doc in DOCS_BY_LEVEL[proveedor.nivel]:
        db.session.add(Documento(expediente_id=expediente.id, tipo=tipo_doc, subido=False))

    log_event(
        "folios",
        folio.id,
        "crear",
        {"proveedor_id": proveedor.id, "empresa_id": empresa.id, "periodo": folio.periodo},
        body.get("usuario"),
    )
    db.session.commit()
    calcular_completitud(expediente.id)

    return jsonify(_folio_dict(folio)), 201


@folios_bp.post("/folios/ciclo-mensual")
def generar_ciclo_mensual():
    body = request.get_json(silent=True) or {}
    required = ["empresa_id", "periodo"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    empresa = Empresa.query.get_or_404(int(body["empresa_id"]))
    periodo = str(body["periodo"])

    folios_base = (
        Folio.query.filter(Folio.empresa_id == empresa.id, Folio.estado == "activo")
        .order_by(Folio.creado_en.asc())
        .all()
    )
    if not folios_base:
        return jsonify({"error": "No hay folios activos base en la empresa para generar ciclo mensual"}), 400

    existentes = {
        f.proveedor_id
        for f in Folio.query.filter(Folio.empresa_id == empresa.id, Folio.periodo == periodo).all()
    }
    rows = Folio.query.with_entities(Folio.numero).all()
    nums = [int(n) for (n,) in rows if isinstance(n, str) and n.isdigit()]
    next_num = max(nums) + 1 if nums else 10001

    creados = []
    for base in folios_base:
        if base.proveedor_id in existentes:
            continue
        folio = Folio(
            numero=str(next_num),
            proveedor_id=base.proveedor_id,
            empresa_id=empresa.id,
            presupuesto=base.presupuesto,
            periodo=periodo,
            fecha_limite_entrega=_fecha_limite_por_periodo(periodo),
            estado="activo",
        )
        next_num += 1
        db.session.add(folio)
        db.session.flush()

        expediente = Expediente(folio_id=folio.id, completitud=0.0, pago_bloqueado=True)
        db.session.add(expediente)
        db.session.flush()

        for tipo_doc in DOCS_BY_LEVEL[base.proveedor.nivel]:
            db.session.add(Documento(expediente_id=expediente.id, tipo=tipo_doc, subido=False))

        log_event(
            "folios",
            folio.id,
            "crear_ciclo_mensual",
            {"empresa_id": empresa.id, "periodo": periodo, "proveedor_id": base.proveedor_id},
            body.get("usuario"),
        )
        creados.append(folio)

    db.session.commit()
    for folio in creados:
        calcular_completitud(folio.expediente.id)

    return jsonify(
        {
            "empresa_id": empresa.id,
            "empresa_nombre": empresa.nombre,
            "periodo": periodo,
            "folios_creados": len(creados),
            "items": [_folio_dict(f) for f in creados],
        }
    )


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
