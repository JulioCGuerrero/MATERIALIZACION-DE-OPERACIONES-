from ..models import EfosRegistro


def normalizar_rfc(rfc: str) -> str:
    return (rfc or "").strip().upper()


def esta_en_efos(rfc: str) -> bool:
    value = normalizar_rfc(rfc)
    if not value:
        return False
    row = EfosRegistro.query.filter_by(rfc=value, publicado_en_sat=True).first()
    return row is not None
