from calendar import monthrange
from datetime import date

from ..extensions import db
from ..models import Documento, Empresa, Expediente, Folio
from .auditoria import log_event
from .bloqueo import calcular_completitud
from .catalogo import DOCS_BY_LEVEL


def fecha_limite_por_periodo(periodo: str) -> date:
    year, month = [int(x) for x in periodo.split("-")]
    return date(year, month, monthrange(year, month)[1])


def generar_ciclo_mensual_empresa(empresa: Empresa, periodo: str, usuario: str | None = None) -> list[Folio]:
    folios_base = (
        Folio.query.filter(Folio.empresa_id == empresa.id, Folio.estado == "activo")
        .order_by(Folio.creado_en.asc())
        .all()
    )
    if not folios_base:
        return []

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
            fecha_limite_entrega=fecha_limite_por_periodo(periodo),
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
            usuario,
        )
        creados.append(folio)

    db.session.commit()
    for folio in creados:
        calcular_completitud(folio.expediente.id)
    return creados
