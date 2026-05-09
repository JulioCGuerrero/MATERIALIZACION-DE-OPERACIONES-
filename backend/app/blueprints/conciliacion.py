from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Traspaso
from ..services.auditoria import log_event

conciliacion_bp = Blueprint("conciliacion", __name__)


@conciliacion_bp.post("/conciliacion/estado_cuenta")
def analizar_estado_cuenta():
    archivo = request.files.get("archivo")
    usuario = request.form.get("usuario", "IA")
    empresa_id = request.form.get("empresa_id", type=int)
    proveedor_id = request.form.get("proveedor_id", type=int)

    if not archivo:
        return jsonify({"error": "Debes enviar un archivo en el campo 'archivo'"}), 400

    filename = secure_filename(archivo.filename or "estado_cuenta.pdf")
    upload_dir = Path(current_app.config["BASE_DIR"]) / "uploads" / "conciliacion"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    archivo.save(file_path)

    q = Traspaso.query.join(Traspaso.folio)
    if empresa_id:
        q = q.filter(Traspaso.folio.has(empresa_id=empresa_id))
    if proveedor_id:
        q = q.filter(Traspaso.folio.has(proveedor_id=proveedor_id))
    traspasos = q.all()

    conciliados = 0
    alertas = []
    for t in traspasos:
        exp = t.folio.expediente
        bloqueado = exp.pago_bloqueado if exp else True
        if (not bloqueado) and (not t.excede_presup):
            conciliados += 1
            continue

        motivos = []
        if bloqueado:
            motivos.append("materialidad incompleta")
        if t.excede_presup:
            motivos.append("excede presupuesto")

        alertas.append(
            {
                "traspaso_id": t.id,
                "folio": t.folio.numero,
                "proveedor": t.folio.proveedor.nombre,
                "monto": t.monto,
                "motivo": " + ".join(motivos),
            }
        )

    log_event(
        "audit_log",
        0,
        "conciliacion_ia",
        {
            "archivo": filename,
            "conciliados": conciliados,
            "alertas": len(alertas),
            "empresa_id": empresa_id,
            "proveedor_id": proveedor_id,
        },
        usuario,
    )

    for a in alertas:
        log_event("traspasos", a["traspaso_id"], "alerta_ia", a, usuario)

    db.session.commit()

    return jsonify(
        {
            "archivo": filename,
            "conciliados": conciliados,
            "total": len(traspasos),
            "filtros": {"empresa_id": empresa_id, "proveedor_id": proveedor_id},
            "alertas": alertas,
        }
    )
