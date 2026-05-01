from datetime import datetime

from ..models import Empresa
from .alertas import generar_alertas
from .ciclos import generar_ciclo_mensual_empresa


def ejecutar_automatizacion(periodo: str | None = None, usuario: str | None = "sistema_auto") -> dict:
    periodo_target = periodo or datetime.now().strftime("%Y-%m")
    empresas = Empresa.query.filter_by(activo=True).order_by(Empresa.nombre.asc()).all()

    resumen_empresas = []
    total_folios = 0
    for empresa in empresas:
        creados = generar_ciclo_mensual_empresa(empresa, periodo_target, usuario)
        total_folios += len(creados)
        resumen_empresas.append(
            {
                "empresa_id": empresa.id,
                "empresa_nombre": empresa.nombre,
                "folios_creados": len(creados),
            }
        )

    alertas = generar_alertas(periodo_target)
    return {
        "periodo": periodo_target,
        "empresas_procesadas": len(empresas),
        "folios_creados": total_folios,
        "alertas_creadas": alertas.get("creadas", 0),
        "detalle_empresas": resumen_empresas,
    }
