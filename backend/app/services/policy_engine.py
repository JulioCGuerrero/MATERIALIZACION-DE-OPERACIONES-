from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from sqlalchemy import inspect

from ..extensions import db
from ..models import Empresa, Expediente, PolicyEvaluation, PolicySet, PolicyVersion
from .catalogo import DOCS_BY_LEVEL, LEVEL_LABELS, LEVEL_RISK


DEFAULT_POLICY = {
    "classification": {
        "level4_min_monto": 500000,
        "level3_tipos": ["consultoria", "outsourcing"],
        "level2_tipos": ["materia"],
        "nivel_up_por_tipo_empresa": ["constructora", "industrial", "financiera"],
    },
    "gates": {
        "min_completitud_para_pago": 100.0,
    },
    "semaforo": {
        "amarillo_min": 70.0,
        "verde_min": 90.0,
        "efos_critico_si_no_ok": True,
    },
}


def _deep_merge(base: dict, patch: dict) -> dict:
    out = deepcopy(base)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _ensure_policy_tables() -> None:
    inspector = inspect(db.engine)
    required = {"policy_sets", "policy_versions", "policy_evaluations"}
    existing = set(inspector.get_table_names())
    if not required.issubset(existing):
        db.create_all()


def get_policy_status(empresa_id: int) -> dict:
    _ensure_policy_tables()
    policy_set = PolicySet.query.filter_by(empresa_id=empresa_id).first()
    if not policy_set or not policy_set.activa_version_id:
        return {"has_active_published_policy": False, "reason": "no_policy_set"}
    active = PolicyVersion.query.get(policy_set.activa_version_id)
    if not active:
        return {"has_active_published_policy": False, "reason": "active_version_not_found"}
    published = active.estado == "active" and active.publicado_en is not None
    return {
        "has_active_published_policy": bool(published),
        "reason": "ok" if published else "active_not_published",
        "policy_version_id": active.id,
        "policy_version": active.version,
        "estado": active.estado,
        "publicado_en": active.publicado_en.isoformat() if active.publicado_en else None,
    }


def get_or_create_policy_set(empresa_id: int, creado_por: str | None = None) -> PolicySet:
    _ensure_policy_tables()
    policy_set = PolicySet.query.filter_by(empresa_id=empresa_id).first()
    if policy_set:
        return policy_set

    policy_set = PolicySet(empresa_id=empresa_id)
    db.session.add(policy_set)
    db.session.flush()

    v1 = PolicyVersion(
        policy_set_id=policy_set.id,
        version=1,
        estado="active",
        parametros=deepcopy(DEFAULT_POLICY),
        creado_por=creado_por,
        nota_cambio="Version inicial por defecto",
        publicado_en=datetime.utcnow(),
    )
    db.session.add(v1)
    db.session.flush()

    policy_set.activa_version_id = v1.id
    db.session.commit()
    return policy_set


def get_active_policy(empresa_id: int | None) -> tuple[dict, PolicyVersion | None]:
    if not empresa_id:
        return deepcopy(DEFAULT_POLICY), None

    policy_set = get_or_create_policy_set(empresa_id)
    active = None
    if policy_set.activa_version_id:
        active = PolicyVersion.query.get(policy_set.activa_version_id)

    if not active:
        return deepcopy(DEFAULT_POLICY), None
    return _deep_merge(DEFAULT_POLICY, active.parametros or {}), active


def evaluate_provider_classification(
    *,
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
    policy, active_version = get_active_policy(empresa_id)
    cfg = policy["classification"]

    tipo_l = (tipo or "").strip().lower()
    tipo_empresa_l = (tipo_empresa or "").strip().lower()

    reasons = []
    if tipo_l == "construccion" or monto > float(cfg["level4_min_monto"]):
        nivel = 4
        reasons.append("Regla N4 por tipo construccion o monto alto")
    elif tipo_l in {x.lower() for x in cfg["level3_tipos"]} or (repse and not tiene_fisico):
        nivel = 3
        reasons.append("Regla N3 por servicios intangibles/REPSE")
    elif tipo_l in {x.lower() for x in cfg["level2_tipos"]} or tiene_fisico:
        nivel = 2
        reasons.append("Regla N2 por evidencia fisica/tipo")
    else:
        nivel = 1
        reasons.append("Regla base N1")

    if tipo_empresa_l in {x.lower() for x in cfg["nivel_up_por_tipo_empresa"]}:
        prev = nivel
        nivel = min(4, nivel + 1)
        if nivel != prev:
            reasons.append("Ajuste +1 por riesgo del giro de empresa")

    result = {
        "nivel": nivel,
        "label": LEVEL_LABELS[nivel],
        "documentos": DOCS_BY_LEVEL[nivel],
        "riesgo": LEVEL_RISK[nivel],
        "policy": {
            "empresa_id": empresa_id,
            "policy_version_id": active_version.id if active_version else None,
            "policy_version": active_version.version if active_version else None,
            "source": "policy_version" if active_version else "default",
        },
        "explicacion": reasons,
    }

    if save_evaluation:
        ev = PolicyEvaluation(
            policy_version_id=active_version.id if active_version else None,
            empresa_id=empresa_id,
            proveedor_id=proveedor_id,
            tipo="clasificacion",
            input_payload={
                "tipo": tipo,
                "monto": monto,
                "repse": repse,
                "tiene_fisico": tiene_fisico,
                "tipo_empresa": tipo_empresa,
                "usuario": usuario,
            },
            output_payload=result,
        )
        db.session.add(ev)
        db.session.commit()

    return result


def evaluate_payment_gate(expediente: Expediente) -> dict:
    empresa_id = expediente.folio.empresa_id
    policy, active_version = get_active_policy(empresa_id)
    min_ok = float(policy["gates"].get("min_completitud_para_pago", 100.0))
    puede = (expediente.completitud or 0.0) >= min_ok
    return {
        "puede_pagar": puede,
        "min_completitud": min_ok,
        "policy_version_id": active_version.id if active_version else None,
        "policy_version": active_version.version if active_version else None,
    }


def simulate_policy_impact(empresa_id: int, parametros: dict) -> dict:
    empresa = Empresa.query.get_or_404(empresa_id)
    base, active = get_active_policy(empresa_id)
    simulated = _deep_merge(base, parametros)

    expedientes = (
        Expediente.query.join(Expediente.folio)
        .filter_by(empresa_id=empresa.id)
        .all()
    )

    before_min = float(base["gates"].get("min_completitud_para_pago", 100.0))
    after_min = float(simulated["gates"].get("min_completitud_para_pago", 100.0))

    bloqueados_before = sum(1 for e in expedientes if (e.completitud or 0.0) < before_min)
    bloqueados_after = sum(1 for e in expedientes if (e.completitud or 0.0) < after_min)

    return {
        "empresa_id": empresa.id,
        "policy_version_actual": active.version if active else None,
        "expedientes_evaluados": len(expedientes),
        "bloqueados_actual": bloqueados_before,
        "bloqueados_simulado": bloqueados_after,
        "delta_bloqueados": bloqueados_after - bloqueados_before,
        "parametros_simulados": parametros,
    }
