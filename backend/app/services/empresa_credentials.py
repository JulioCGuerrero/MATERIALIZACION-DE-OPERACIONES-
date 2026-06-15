from __future__ import annotations

import secrets

from ..extensions import db
from ..models import Empresa, EmpresaCredencial


def ensure_empresa_credencial(empresa: Empresa, password: str | None = None) -> tuple[EmpresaCredencial, bool]:
    cred = EmpresaCredencial.query.filter_by(empresa_id=empresa.id).first()
    if cred:
        return cred, False

    cred = EmpresaCredencial(
        empresa_id=empresa.id,
        username=f"empresa_{empresa.id}_portal",
        password=password or secrets.token_urlsafe(8),
        activo=True,
    )
    db.session.add(cred)
    db.session.flush()
    return cred, True


def ensure_all_empresa_credenciales_demo() -> int:
    created = 0
    empresas = Empresa.query.order_by(Empresa.id.asc()).all()
    for empresa in empresas:
        cred = EmpresaCredencial.query.filter_by(empresa_id=empresa.id).first()
        if cred:
            continue
        db.session.add(
            EmpresaCredencial(
                empresa_id=empresa.id,
                username=f"empresa_{empresa.id}_portal",
                password=f"demo-empresa-{empresa.id}",
                activo=True,
            )
        )
        created += 1
    if created:
        db.session.commit()
    return created
