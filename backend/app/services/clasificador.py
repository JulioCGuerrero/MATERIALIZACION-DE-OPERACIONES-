from .catalogo import DOCS_BY_LEVEL, LEVEL_LABELS, LEVEL_RISK


def clasificar_proveedor(
    tipo: str,
    monto: float,
    repse: bool,
    tiene_fisico: bool,
    tipo_empresa: str = "servicios",
) -> dict:
    if tipo == "construccion" or monto > 500_000:
        nivel = 4
    elif tipo in ("consultoria", "outsourcing") or (repse and not tiene_fisico):
        nivel = 3
    elif tipo == "materia" or tiene_fisico:
        nivel = 2
    else:
        nivel = 1

    # Ajuste por giro de empresa cliente: ciertos giros elevan el riesgo fiscal.
    if (tipo_empresa or "").strip().lower() in {"constructora", "industrial", "financiera"}:
        nivel = min(4, nivel + 1)

    return {
        "nivel": nivel,
        "label": LEVEL_LABELS[nivel],
        "documentos": DOCS_BY_LEVEL[nivel],
        "riesgo": LEVEL_RISK[nivel],
    }
