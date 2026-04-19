from ..models import Documento, Expediente, Proveedor


def _estado_ratio(cumplen: int, total: int, critico: bool = False) -> str:
    if total == 0:
        return "verde"
    ratio = (cumplen / total) * 100
    if critico or ratio < 70:
        return "rojo"
    if ratio < 90:
        return "amarillo"
    return "verde"


def _metric(valor_ok: int, total: int, ley: str, etiqueta_ok: str, critico: bool = False) -> dict:
    estado = _estado_ratio(valor_ok, total, critico=critico)
    return {
        "estado": estado,
        "valor": f"{valor_ok}/{total} {etiqueta_ok}",
        "ley": ley,
    }


def calcular_semaforo() -> dict:
    proveedores = Proveedor.query.filter_by(activo=True).all()
    total_prov = len(proveedores)
    efos_ok = sum(1 for p in proveedores if p.efos_ok)
    efos_critico = efos_ok < total_prov

    expedientes = Expediente.query.all()
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
            if (exp.razon_negocio and exp.razon_negocio.strip()) or docs.get("cuestionario_5a"):
                razon_ok += 1

        if exp.folio.proveedor.repse:
            repse_total += 1
            if docs.get("repse"):
                repse_ok += 1

    return {
        "efos": _metric(efos_ok, total_prov, "Art. 69-B CFF", "proveedores OK", critico=efos_critico),
        "cfdi_correcto": _metric(cfdi_ok, total_exp, "Art. 29-A CFF", "expedientes OK"),
        "nom151": _metric(nom151_ok, max(1, sum(1 for e in expedientes if e.folio.proveedor.nivel in (3, 4))), "NOM-151", "contratos OK"),
        "repse": _metric(repse_ok, max(1, repse_total), "LFT / REPSE", "proveedores REPSE OK"),
        "manifiesto": _metric(manifiesto_ok, max(1, manifiesto_total), "Art. 69-B CFF", "manifiestos OK"),
        "razon_negocios": _metric(razon_ok, max(1, razon_total), "Art. 5-A CFF", "análisis OK"),
    }
