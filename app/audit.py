"""Utilidades de auditoria.

Centraliza la creacion de eventos de auditoria para no repetir codigo
en cada modulo/ruta.
"""

from app.extensions import db
from app.models import AuditLog


def log_action(*, user_id, action, entity, entity_id=None, details=None):
    """Crea y persiste un evento de auditoria.

    Parametros nombrados (`*`) hacen mas explicita la llamada y reducen
    errores de orden de argumentos.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id else None,
        details=details,
    )
    db.session.add(entry)
    db.session.commit()
