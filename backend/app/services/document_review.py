from datetime import datetime

from ..models import Documento


EXPECTED_EXT = {
    "cfdi_xml": ".xml",
    "cfdi_pdf": ".pdf",
}


def _endswith(value: str | None, ext: str) -> bool:
    return bool(value and value.lower().endswith(ext))


def validar_documento(doc: Documento) -> dict:
    if not doc.nombre_archivo and not doc.url:
        return {
            "estado": "rechazado",
            "detalle": "Documento sin nombre de archivo ni URL.",
        }

    exp_ext = EXPECTED_EXT.get(doc.tipo)
    if exp_ext:
        ok = _endswith(doc.nombre_archivo, exp_ext) or _endswith(doc.url, exp_ext)
        if not ok:
            return {
                "estado": "observado",
                "detalle": f"Formato esperado para {doc.tipo}: {exp_ext}.",
            }

    return {
        "estado": "valido",
        "detalle": "Validación automática aprobada.",
    }


def aplicar_validacion_documento(doc: Documento, motor: str = "motor_validacion") -> dict:
    result = validar_documento(doc)
    doc.validacion_estado = result["estado"]
    doc.validacion_detalle = result["detalle"]
    doc.validado_en = datetime.utcnow()
    doc.validado_por = motor
    return result
