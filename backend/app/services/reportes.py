from ..models import Folio, Proveedor, Traspaso
from .semaforo import calcular_semaforo


def reporte_por_nivel_data(
    nivel: int | None = None,
    empresa_id: int | None = None,
    proveedor_id: int | None = None,
) -> dict:
    # LEFT JOIN a expediente para no excluir folios/empresas si aún no tienen expediente ligado.
    q = Folio.query.join(Folio.proveedor).outerjoin(Folio.expediente)
    if nivel:
        q = q.filter(Proveedor.nivel == nivel)
    if empresa_id:
        q = q.filter(Folio.empresa_id == empresa_id)
    if proveedor_id:
        q = q.filter(Folio.proveedor_id == proveedor_id)

    folios = q.order_by(Folio.numero.asc()).all()

    data = []
    for f in folios:
        exp = f.expediente
        data.append(
            {
                "folio": f.numero,
                "proveedor": f.proveedor.nombre,
                "empresa_id": f.empresa.id if f.empresa else None,
                "empresa": f.empresa.nombre if f.empresa else "Sin empresa",
                "nivel": f.proveedor.nivel,
                "tipo": f.proveedor.tipo,
                "completitud": exp.completitud if exp else 0.0,
                "pago_bloqueado": exp.pago_bloqueado if exp else True,
                "presupuesto": f.presupuesto,
                "estado_folio": f.estado,
            }
        )

    resumen = {
        "total": len(data),
        "bloqueados": sum(1 for r in data if r["pago_bloqueado"]),
        "completos": sum(1 for r in data if (r["completitud"] or 0) >= 100),
        "por_nivel": {
            "n1": sum(1 for r in data if r["nivel"] == 1),
            "n2": sum(1 for r in data if r["nivel"] == 2),
            "n3": sum(1 for r in data if r["nivel"] == 3),
            "n4": sum(1 for r in data if r["nivel"] == 4),
        },
    }

    return {"resumen": resumen, "items": data}


def reporte_semaforo_data(
    empresa_id: int | None = None,
    proveedor_id: int | None = None,
    nivel: int | None = None,
) -> dict:
    return calcular_semaforo(empresa_id=empresa_id, proveedor_id=proveedor_id, nivel=nivel)


def reporte_trazabilidad_data(
    empresa_id: int | None = None,
    proveedor_id: int | None = None,
    nivel: int | None = None,
) -> dict:
    q = Traspaso.query.join(Traspaso.folio).join(Folio.proveedor)
    if empresa_id:
        q = q.filter(Folio.empresa_id == empresa_id)
    if proveedor_id:
        q = q.filter(Folio.proveedor_id == proveedor_id)
    if nivel:
        q = q.filter(Proveedor.nivel == nivel)
    traspasos = q.order_by(Traspaso.creado_en.desc()).all()

    items = []
    for t in traspasos:
        exp = t.folio.expediente
        items.append(
            {
                "id": t.id,
                "folio": t.folio.numero,
                "proveedor": t.folio.proveedor.nombre,
                "empresa_id": t.folio.empresa.id if t.folio.empresa else None,
                "empresa": t.folio.empresa.nombre if t.folio.empresa else "Sin empresa",
                "nivel": t.folio.proveedor.nivel,
                "materialidad": exp.completitud if exp else 0.0,
                "folio_bancario": t.folio_bancario,
                "monto": t.monto,
                "presupuesto": t.folio.presupuesto,
                "excede_presup": t.excede_presup,
                "pago_bloqueado": exp.pago_bloqueado if exp else True,
            }
        )

    return {"total": len(items), "items": items}
