from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import EfosRegistro
from ..services.efos import esta_en_efos, normalizar_rfc

efos_bp = Blueprint("efos", __name__)


@efos_bp.get("/efos/consultar")
def consultar_efos():
    rfc = request.args.get("rfc", type=str)
    if not rfc:
        return jsonify({"error": "Debes enviar rfc"}), 400
    value = normalizar_rfc(rfc)
    return jsonify({"rfc": value, "en_efos": esta_en_efos(value)})


@efos_bp.post("/efos/cargar")
def cargar_efos():
    body = request.get_json(silent=True) or {}
    rfcs = body.get("rfcs", [])
    if not isinstance(rfcs, list) or not rfcs:
        return jsonify({"error": "Debes enviar rfcs como lista no vacía"}), 400

    created = 0
    updated = 0
    for raw in rfcs:
        value = normalizar_rfc(str(raw))
        if not value:
            continue
        row = EfosRegistro.query.filter_by(rfc=value).first()
        if row:
            row.publicado_en_sat = True
            row.fuente = body.get("fuente", row.fuente or "sat")
            updated += 1
        else:
            db.session.add(
                EfosRegistro(
                    rfc=value,
                    publicado_en_sat=True,
                    fuente=body.get("fuente", "sat"),
                )
            )
            created += 1
    db.session.commit()
    return jsonify({"creados": created, "actualizados": updated})
