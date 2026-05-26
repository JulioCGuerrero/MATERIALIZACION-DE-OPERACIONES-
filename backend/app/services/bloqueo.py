from ..extensions import db
from ..models import Expediente
from .auditoria import log_event
from .policy_engine import evaluate_payment_gate


def calcular_completitud(expediente_id: int) -> float:
    expediente = db.session.get(Expediente, expediente_id)
    if not expediente:
        raise ValueError(f"Expediente {expediente_id} no existe")
    total = len(expediente.documentos)
    subidos = sum(1 for d in expediente.documentos if d.subido and d.validacion_estado == "valido")

    completitud = 0.0 if total == 0 else round((subidos / total) * 100, 2)
    was_blocked = expediente.pago_bloqueado
    expediente.completitud = completitud
    gate = evaluate_payment_gate(expediente)
    expediente.pago_bloqueado = not gate["puede_pagar"]

    if was_blocked != expediente.pago_bloqueado:
        log_event(
            "expedientes",
            expediente.id,
            "liberar" if not expediente.pago_bloqueado else "bloquear",
            {
                "completitud": completitud,
                "folio": expediente.folio.numero,
            },
        )

    db.session.commit()
    return completitud


def puede_pagar(expediente_id: int) -> dict:
    expediente = db.session.get(Expediente, expediente_id)
    if not expediente:
        raise ValueError(f"Expediente {expediente_id} no existe")
    calcular_completitud(expediente_id)
    expediente = Expediente.query.get(expediente_id)

    faltantes = [d.tipo for d in expediente.documentos if not (d.subido and d.validacion_estado == "valido")]
    observados = [d.tipo for d in expediente.documentos if d.subido and d.validacion_estado in ("observado", "rechazado")]
    return {
        "puede_pagar": not expediente.pago_bloqueado,
        "completitud": expediente.completitud,
        "min_completitud_requerida": evaluate_payment_gate(expediente)["min_completitud"],
        "documentos_faltantes": faltantes,
        "documentos_observados": observados,
    }
