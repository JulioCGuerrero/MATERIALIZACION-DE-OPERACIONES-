from ..models import Expediente, Folio, Proveedor
from .policy_engine import get_active_policy


def _estado_ratio(
    cumplen: int,
    total: int,
    critico: bool = False,
    amarillo_min: float = 70.0,
    verde_min: float = 90.0,
) -> str:
    if total == 0:
        return "verde"
    ratio = (cumplen / total) * 100
    if critico or ratio < amarillo_min:
        return "rojo"
    if ratio < verde_min:
        return "amarillo"
    return "verde"


def _metric(
    valor_ok: int,
    total: int,
    ley: str,
    etiqueta_ok: str,
    critico: bool = False,
    amarillo_min: float = 70.0,
    verde_min: float = 90.0,
) -> dict:
    estado = _estado_ratio(valor_ok, total, critico=critico, amarillo_min=amarillo_min, verde_min=verde_min)
    return {
        "estado": estado,
        "valor": f"{valor_ok}/{total} {etiqueta_ok}",
        "ley": ley,
    }


def calcular_semaforo(
    empresa_id: int | None = None,
    proveedor_id: int | None = None,
    nivel: int | None = None,
) -> dict:
    policy, active_version = get_active_policy(empresa_id)
    yellow = float(policy["semaforo"].get("amarillo_min", 70.0))
    green = float(policy["semaforo"].get("verde_min", 90.0))

    proveedores_q = Proveedor.query.filter_by(activo=True)
    if proveedor_id:
        proveedores_q = proveedores_q.filter(Proveedor.id == proveedor_id)
    if nivel:
        proveedores_q = proveedores_q.filter(Proveedor.nivel == nivel)
    if empresa_id:
        proveedores_q = proveedores_q.join(Proveedor.folios).filter(Folio.empresa_id == empresa_id).distinct()
    proveedores = proveedores_q.all()
    total_prov = len(proveedores)
    efos_ok = sum(1 for p in proveedores if p.efos_ok)
    efos_critico = (efos_ok < total_prov) if policy["semaforo"].get("efos_critico_si_no_ok", True) else False

    expedientes_q = Expediente.query.join(Expediente.folio).join(Folio.proveedor)
    if empresa_id:
        expedientes_q = expedientes_q.filter(Folio.empresa_id == empresa_id)
    if proveedor_id:
        expedientes_q = expedientes_q.filter(Folio.proveedor_id == proveedor_id)
    if nivel:
        expedientes_q = expedientes_q.filter(Proveedor.nivel == nivel)
    expedientes = expedientes_q.all()
    total_exp = len(expedientes)

    cfdi_ok = 0
    nom151_ok = 0
    repse_total = 0
    repse_ok = 0
    manifiesto_total = 0
    manifiesto_ok = 0
    razon_total = 0
    razon_ok = 0

    for exp in expedientes:
        docs = {d.tipo: d.subido for d in exp.documentos}
        if docs.get("cfdi_xml") and docs.get("cfdi_pdf"):
            cfdi_ok += 1

        nivel = exp.folio.proveedor.nivel
        if nivel in (3, 4):
            if docs.get("contrato_nom151"):
                nom151_ok += 1
            manifiesto_total += 1
            if docs.get("manifiesto_materialidad") or exp.manifiesto:
                manifiesto_ok += 1
            razon_total += 1
            if exp.razon_negocio and exp.razon_negocio.strip():
                razon_ok += 1

        if exp.folio.proveedor.repse:
            repse_total += 1
            if docs.get("repse"):
                repse_ok += 1

    return {
        "efos": _metric(efos_ok, total_prov, "Art. 69-B CFF", "proveedores OK", critico=efos_critico, amarillo_min=yellow, verde_min=green),
        "cfdi_correcto": _metric(cfdi_ok, total_exp, "Art. 29-A CFF", "expedientes OK", amarillo_min=yellow, verde_min=green),
        "nom151": _metric(nom151_ok, max(1, sum(1 for e in expedientes if e.folio.proveedor.nivel in (3, 4))), "NOM-151", "contratos OK", amarillo_min=yellow, verde_min=green),
        "repse": _metric(repse_ok, max(1, repse_total), "LFT / REPSE", "proveedores REPSE OK", amarillo_min=yellow, verde_min=green),
        "manifiesto": _metric(manifiesto_ok, max(1, manifiesto_total), "Art. 69-B CFF", "manifiestos OK", amarillo_min=yellow, verde_min=green),
        "razon_negocios": _metric(razon_ok, max(1, razon_total), "Art. 5-A CFF", "análisis OK", amarillo_min=yellow, verde_min=green),
        "policy": {
            "policy_version_id": active_version.id if active_version else None,
            "policy_version": active_version.version if active_version else None,
        },
    }
