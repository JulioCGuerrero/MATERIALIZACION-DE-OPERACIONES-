from datetime import date

from ..extensions import db
from ..models import Alerta, Expediente, Folio, Proveedor
from .semaforo import calcular_semaforo


def _crear_alerta_unica(
    tipo: str,
    severidad: str,
    mensaje: str,
    proveedor_id: int | None = None,
    empresa_id: int | None = None,
    folio_id: int | None = None,
    expediente_id: int | None = None,
    periodo: str | None = None,
):
    existe = (
        Alerta.query.filter_by(
            tipo=tipo,
            estado="activa",
            proveedor_id=proveedor_id,
            empresa_id=empresa_id,
            folio_id=folio_id,
            expediente_id=expediente_id,
            periodo=periodo,
        )
        .order_by(Alerta.id.desc())
        .first()
    )
    if existe:
        return None

    a = Alerta(
        tipo=tipo,
        severidad=severidad,
        mensaje=mensaje,
        proveedor_id=proveedor_id,
        empresa_id=empresa_id,
        folio_id=folio_id,
        expediente_id=expediente_id,
        periodo=periodo,
        estado="activa",
        origen="auto",
    )
    db.session.add(a)
    return a


def generar_alertas(periodo: str | None = None) -> dict:
    creadas = []
    today = date.today()

    proveedores = Proveedor.query.filter_by(activo=True).all()
    for p in proveedores:
        if not p.efos_ok:
            x = _crear_alerta_unica(
                tipo="efos",
                severidad="rojo",
                mensaje=f"Proveedor {p.nombre} ({p.rfc}) aparece en EFOS. Registro/bloqueo recomendado.",
                proveedor_id=p.id,
            )
            if x:
                creadas.append(x)

    q = Expediente.query.join(Expediente.folio).filter(Folio.estado == "activo")
    if periodo:
        q = q.filter(Folio.periodo == periodo)
    expedientes = q.all()

    for exp in expedientes:
        folio = exp.folio
        if exp.completitud >= 100.0:
            continue
        if not folio.fecha_limite_entrega:
            continue

        dias = (folio.fecha_limite_entrega - today).days
        if dias < 0:
            x = _crear_alerta_unica(
                tipo="reporte_vencido",
                severidad="rojo",
                mensaje=f"Reporte vencido para folio {folio.numero} ({folio.periodo}). Completitud {exp.completitud}%.",
                proveedor_id=folio.proveedor_id,
                empresa_id=folio.empresa_id,
                folio_id=folio.id,
                expediente_id=exp.id,
                periodo=folio.periodo,
            )
            if x:
                creadas.append(x)
        elif dias <= 5:
            x = _crear_alerta_unica(
                tipo="reporte_por_vencer",
                severidad="amarillo",
                mensaje=f"Entrega próxima ({dias} días) para folio {folio.numero} ({folio.periodo}). Completitud {exp.completitud}%.",
                proveedor_id=folio.proveedor_id,
                empresa_id=folio.empresa_id,
                folio_id=folio.id,
                expediente_id=exp.id,
                periodo=folio.periodo,
            )
            if x:
                creadas.append(x)

    semaforo = calcular_semaforo()
    if semaforo["efos"]["estado"] == "rojo":
        x = _crear_alerta_unica(
            tipo="semaforo_efos_rojo",
            severidad="rojo",
            mensaje="Semáforo fiscal EFOS en rojo (Art. 69-B CFF).",
            periodo=periodo,
        )
        if x:
            creadas.append(x)

    db.session.commit()
    return {"creadas": len(creadas)}
