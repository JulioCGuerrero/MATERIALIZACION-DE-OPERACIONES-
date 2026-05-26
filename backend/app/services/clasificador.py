from .policy_engine import evaluate_provider_classification


def clasificar_proveedor(
    tipo: str,
    monto: float,
    repse: bool,
    tiene_fisico: bool,
    tipo_empresa: str = "servicios",
    empresa_id: int | None = None,
    proveedor_id: int | None = None,
    usuario: str | None = None,
    save_evaluation: bool = False,
) -> dict:
    return evaluate_provider_classification(
        tipo=tipo,
        monto=monto,
        repse=repse,
        tiene_fisico=tiene_fisico,
        tipo_empresa=tipo_empresa,
        empresa_id=empresa_id,
        proveedor_id=proveedor_id,
        usuario=usuario,
        save_evaluation=save_evaluation,
    )
