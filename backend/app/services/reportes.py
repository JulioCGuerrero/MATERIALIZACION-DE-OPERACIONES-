from ..models import Folio, Proveedor, Traspaso
from .semaforo import calcular_semaforo


def reporte_por_nivel_data(nivel: int | None = None) -> dict:
    q = Folio.query.join(Folio.proveedor).join(Folio.expediente)
    if nivel:
        q = q.filter(Proveedor.nivel == nivel)

    folios = q.order_by(Folio.numero.asc()).all()

    data = []
    for f in folios:
        exp = f.expediente
        data.append(
            {
                "folio": f.numero,
                "proveedor": f.proveedor.nombre,
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


def reporte_semaforo_data() -> dict:
    return calcular_semaforo()


def reporte_trazabilidad_data() -> dict:
    traspasos = Traspaso.query.join(Traspaso.folio).join(Folio.proveedor).order_by(Traspaso.creado_en.desc()).all()

    items = []
    for t in traspasos:
        exp = t.folio.expediente
        items.append(
            {
                "id": t.id,
                "folio": t.folio.numero,
                "proveedor": t.folio.proveedor.nombre,
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
