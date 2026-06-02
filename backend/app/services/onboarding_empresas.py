from __future__ import annotations

import json
from datetime import date

from ..models import Empresa, EmpresaCuentaBancaria, EmpresaDocumento

DOCS_REQUERIDOS_EMPRESA = [
    "constancia_fiscal",
    "acta_constitutiva",
    "poder_representante",
    "identificacion_representante",
    "comprobante_domicilio_fiscal",
    "opinion_32d",
    "carta_bancaria_cuentas",
    "estado_cuenta_bancario",
    "politica_autorizacion_pagos",
]

REGLAS_NEGOCIO_REQUERIDAS = [
    "flujo_alta_proveedores",
    "regla_no_pago_sin_expediente",
    "politica_cambio_cuenta_proveedor",
    "conciliacion_bancaria_mensual",
]


def _doc_vigente(doc: EmpresaDocumento) -> bool:
    return doc.vigente_hasta is None or doc.vigente_hasta >= date.today()


def empresa_onboarding_status(empresa: Empresa) -> dict:
    docs_by_tipo = {d.tipo: d for d in empresa.documentos}
    docs_detalle = []
    docs_ok = 0
    for tipo in DOCS_REQUERIDOS_EMPRESA:
        doc = docs_by_tipo.get(tipo)
        ok = bool(doc and doc.estado_validacion == "valido" and _doc_vigente(doc))
        if ok:
            docs_ok += 1
        docs_detalle.append(
            {
                "tipo": tipo,
                "presente": bool(doc),
                "estado_validacion": doc.estado_validacion if doc else "faltante",
                "vigente": _doc_vigente(doc) if doc else False,
                "ok": ok,
            }
        )

    reglas_raw = empresa.reglas_negocio or {}
    if isinstance(reglas_raw, str):
        try:
            reglas = json.loads(reglas_raw) if reglas_raw.strip() else {}
        except Exception:
            reglas = {}
    elif isinstance(reglas_raw, dict):
        reglas = reglas_raw
    else:
        reglas = {}
    reglas_detalle = []
    reglas_ok = 0
    for regla in REGLAS_NEGOCIO_REQUERIDAS:
        ok = bool(reglas.get(regla))
        if ok:
            reglas_ok += 1
        reglas_detalle.append({"regla": regla, "ok": ok})

    cuentas_activas = [c for c in empresa.cuentas_bancarias if c.activa]
    cuentas_validadas = [c for c in cuentas_activas if c.validada]
    cuentas_ok = len(cuentas_validadas) > 0

    total_checks = len(DOCS_REQUERIDOS_EMPRESA) + len(REGLAS_NEGOCIO_REQUERIDAS) + 1
    passed_checks = docs_ok + reglas_ok + (1 if cuentas_ok else 0)
    completitud = round((passed_checks / total_checks) * 100, 2) if total_checks else 0.0

    puede_aprobarse = docs_ok == len(DOCS_REQUERIDOS_EMPRESA) and reglas_ok == len(REGLAS_NEGOCIO_REQUERIDAS) and cuentas_ok
    return {
        "empresa_id": empresa.id,
        "onboarding_status": empresa.onboarding_status,
        "completitud": completitud,
        "puede_aprobarse": puede_aprobarse,
        "documentos": {"ok": docs_ok, "total": len(DOCS_REQUERIDOS_EMPRESA), "detalle": docs_detalle},
        "reglas_negocio": {"ok": reglas_ok, "total": len(REGLAS_NEGOCIO_REQUERIDAS), "detalle": reglas_detalle},
        "cuentas_bancarias": {
            "activas": len(cuentas_activas),
            "validadas": len(cuentas_validadas),
            "ok": cuentas_ok,
        },
    }


def empresa_habilitada_para_proveedores(empresa: Empresa) -> tuple[bool, dict]:
    status = empresa_onboarding_status(empresa)
    ok = empresa.activo and empresa.onboarding_status == "aprobada" and status["puede_aprobarse"]
    return ok, status
