from datetime import datetime

from flask import Blueprint, jsonify, request

from ..models import AuditLog

audit_log_bp = Blueprint("audit_log", __name__)


@audit_log_bp.get("/audit_log")
def listar_audit_log():
    q = AuditLog.query

    if request.args.get("tabla"):
        q = q.filter(AuditLog.tabla == request.args["tabla"])
    if request.args.get("accion"):
        q = q.filter(AuditLog.accion == request.args["accion"])
    if request.args.get("desde"):
        desde = datetime.fromisoformat(request.args["desde"])
        q = q.filter(AuditLog.creado_en >= desde)

    rows = q.order_by(AuditLog.creado_en.desc()).all()
    return jsonify(
        [
            {
                "id": r.id,
                "tabla": r.tabla,
                "tabla_id": r.tabla_id,
                "accion": r.accion,
                "detalle": r.detalle,
                "usuario": r.usuario,
                "creado_en": r.creado_en.isoformat() if r.creado_en else None,
            }
            for r in rows
        ]
    )
