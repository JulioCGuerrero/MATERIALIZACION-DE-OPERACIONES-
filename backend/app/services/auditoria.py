import json

from ..extensions import db
from ..models import AuditLog


def log_event(tabla: str, tabla_id: int, accion: str, detalle: dict | None = None, usuario: str | None = None) -> None:
    entry = AuditLog(
        tabla=tabla,
        tabla_id=tabla_id,
        accion=accion,
        detalle=json.dumps(detalle or {}, ensure_ascii=False),
        usuario=usuario,
    )
    db.session.add(entry)
