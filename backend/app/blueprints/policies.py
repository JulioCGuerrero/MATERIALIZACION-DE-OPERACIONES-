from copy import deepcopy
from datetime import datetime
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Empresa, EmpresaDocumento, Folio, PolicyEvaluation, PolicySet, PolicyVersion, Proveedor
from ..services.catalogo import DOCS_BY_LEVEL
from ..services.policy_engine import (
    DEFAULT_POLICY,
    evaluate_provider_classification,
    get_active_policy,
    get_or_create_policy_set,
    get_policy_status,
    simulate_policy_impact,
)
from ..services.storage import save_upload

policies_bp = Blueprint("policies", __name__)


def _policy_document_from_version(version: PolicyVersion | None) -> dict | None:
    if not version or not isinstance(version.parametros, dict):
        return None
    doc = version.parametros.get("_policy_document")
    return doc if isinstance(doc, dict) else None


@policies_bp.get("/empresas/<int:empresa_id>/policy")
def get_policy(empresa_id: int):
    Empresa.query.get_or_404(empresa_id)
    policy, active = get_active_policy(empresa_id)
    doc = _policy_document_from_version(active)
    return jsonify(
        {
            "empresa_id": empresa_id,
            "policy": policy,
            "active_version": {
                "id": active.id,
                "version": active.version,
                "estado": active.estado,
                "publicado_en": active.publicado_en.isoformat() if active and active.publicado_en else None,
                "documento": doc,
            }
            if active
            else None,
        }
    )


@policies_bp.get("/empresas/<int:empresa_id>/policy/status")
def get_policy_status_endpoint(empresa_id: int):
    Empresa.query.get_or_404(empresa_id)
    status = get_policy_status(empresa_id)
    status["empresa_id"] = empresa_id
    return jsonify(status)


@policies_bp.post("/empresas/<int:empresa_id>/policy/draft")
def create_policy_draft(empresa_id: int):
    Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    parametros = body.get("parametros") or {}
    usuario = body.get("usuario")
    nota = body.get("nota_cambio")

    policy_set = get_or_create_policy_set(empresa_id, creado_por=usuario)
    current = PolicyVersion.query.get(policy_set.activa_version_id) if policy_set.activa_version_id else None
    base_params = current.parametros if current else {}

    latest = (
        PolicyVersion.query.filter_by(policy_set_id=policy_set.id)
        .order_by(PolicyVersion.version.desc())
        .first()
    )
    next_version = (latest.version if latest else 0) + 1

    draft = PolicyVersion(
        policy_set_id=policy_set.id,
        version=next_version,
        estado="draft",
        parametros={**base_params, **parametros},
        creado_por=usuario,
        nota_cambio=nota,
    )
    db.session.add(draft)
    db.session.commit()

    return jsonify({"ok": True, "draft_version_id": draft.id, "version": draft.version}), 201


@policies_bp.post("/empresas/<int:empresa_id>/policy/upload")
def upload_policy_document(empresa_id: int):
    empresa = Empresa.query.get_or_404(empresa_id)
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "Debes adjuntar un archivo de política en el campo 'archivo'"}), 400

    usuario = request.form.get("usuario") or "frontend"
    nota = (request.form.get("nota_cambio") or "Carga de política operativa").strip()
    filename = secure_filename(archivo.filename or f"politica_empresa_{empresa.id}.pdf")
    public_url = save_upload(archivo, f"policies/{empresa.id}/{filename}")

    doc = EmpresaDocumento.query.filter_by(empresa_id=empresa.id, tipo="politica_autorizacion_pagos").first()
    if not doc:
        doc = EmpresaDocumento(empresa_id=empresa.id, tipo="politica_autorizacion_pagos")
        db.session.add(doc)
    doc.nombre_archivo = filename
    doc.url = public_url
    doc.estado_validacion = "valido"
    doc.subido_por = usuario
    doc.validado_por = usuario
    doc.subido_en = datetime.utcnow()
    doc.validado_en = datetime.utcnow()

    policy_set = get_or_create_policy_set(empresa.id, creado_por=usuario)
    current = PolicyVersion.query.get(policy_set.activa_version_id) if policy_set.activa_version_id else None
    latest = (
        PolicyVersion.query.filter_by(policy_set_id=policy_set.id)
        .order_by(PolicyVersion.version.desc())
        .first()
    )
    next_version = (latest.version if latest else 0) + 1
    base_params = deepcopy(current.parametros) if current and isinstance(current.parametros, dict) else deepcopy(DEFAULT_POLICY)
    base_params["_policy_document"] = {
        "nombre_archivo": filename,
        "url": public_url,
        "subido_por": usuario,
        "subido_en": datetime.utcnow().isoformat(),
        "nota_cambio": nota,
    }

    version = PolicyVersion(
        policy_set_id=policy_set.id,
        version=next_version,
        estado="active",
        parametros=base_params,
        creado_por=usuario,
        nota_cambio=nota,
        publicado_en=datetime.utcnow(),
    )
    db.session.add(version)
    db.session.flush()

    PolicyVersion.query.filter(
        PolicyVersion.policy_set_id == policy_set.id,
        PolicyVersion.id != version.id,
        PolicyVersion.estado == "active",
    ).update({"estado": "archived"}, synchronize_session=False)
    policy_set.activa_version_id = version.id
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "empresa_id": empresa.id,
            "empresa_nombre": empresa.nombre,
            "active_version_id": version.id,
            "version": version.version,
            "documento": base_params["_policy_document"],
            "policy_status": get_policy_status(empresa.id),
        }
    ), 201


@policies_bp.post("/empresas/<int:empresa_id>/policy/publish/<int:version_id>")
def publish_policy(empresa_id: int, version_id: int):
    Empresa.query.get_or_404(empresa_id)
    policy_set = get_or_create_policy_set(empresa_id)
    version = PolicyVersion.query.filter_by(id=version_id, policy_set_id=policy_set.id).first_or_404()

    version.estado = "active"
    from datetime import datetime

    version.publicado_en = datetime.utcnow()
    policy_set.activa_version_id = version.id

    PolicyVersion.query.filter(
        PolicyVersion.policy_set_id == policy_set.id,
        PolicyVersion.id != version.id,
        PolicyVersion.estado == "active",
    ).update({"estado": "archived"}, synchronize_session=False)

    db.session.commit()
    return jsonify({"ok": True, "active_version_id": version.id, "version": version.version})


@policies_bp.get("/empresas/<int:empresa_id>/policy/versions")
def list_versions(empresa_id: int):
    Empresa.query.get_or_404(empresa_id)
    policy_set = PolicySet.query.filter_by(empresa_id=empresa_id).first()
    if not policy_set:
        return jsonify([])

    versions = (
        PolicyVersion.query.filter_by(policy_set_id=policy_set.id)
        .order_by(PolicyVersion.version.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": v.id,
                "version": v.version,
                "estado": v.estado,
                "creado_por": v.creado_por,
                "nota_cambio": v.nota_cambio,
                "creado_en": v.creado_en.isoformat() if v.creado_en else None,
                "publicado_en": v.publicado_en.isoformat() if v.publicado_en else None,
                "documento": _policy_document_from_version(v),
            }
            for v in versions
        ]
    )


@policies_bp.post("/empresas/<int:empresa_id>/policy/simulate")
def simulate_policy(empresa_id: int):
    Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    parametros = body.get("parametros") or {}
    return jsonify(simulate_policy_impact(empresa_id, parametros))


@policies_bp.get("/policy/context")
def policy_context():
    empresa_id = request.args.get("empresa_id", type=int)
    proveedor_id = request.args.get("proveedor_id", type=int)
    if not empresa_id or not proveedor_id:
        return jsonify({"error": "Debes enviar empresa_id y proveedor_id"}), 400

    empresa = Empresa.query.get_or_404(empresa_id)
    proveedor = Proveedor.query.get_or_404(proveedor_id)
    folio = (
        Folio.query.filter_by(empresa_id=empresa.id, proveedor_id=proveedor.id)
        .order_by(Folio.creado_en.desc())
        .first()
    )
    if not folio:
        return jsonify({"error": "Proveedor no asociado a la empresa"}), 404

    policy, active = get_active_policy(empresa.id)
    clasificacion = evaluate_provider_classification(
        tipo=proveedor.tipo,
        monto=float(folio.presupuesto or 0.0),
        repse=bool(proveedor.repse),
        tiene_fisico=bool(proveedor.tiene_fisico),
        tipo_empresa=empresa.tipo_empresa or "servicios",
        empresa_id=empresa.id,
        proveedor_id=proveedor.id,
        save_evaluation=False,
    )
    exp = folio.expediente
    min_comp = float(policy.get("gates", {}).get("min_completitud_para_pago", 100.0))
    completitud = float(exp.completitud or 0.0) if exp else 0.0
    gap = round(max(0.0, min_comp - completitud), 2)
    docs_total = len(exp.documentos) if exp else 0
    docs_ok = sum(1 for d in (exp.documentos if exp else []) if d.subido and d.validacion_estado == "valido")
    docs_pendientes = [d.tipo for d in (exp.documentos if exp else []) if not d.subido]
    docs_observados = [
        d.tipo for d in (exp.documentos if exp else []) if d.subido and d.validacion_estado in ("observado", "rechazado")
    ]
    last_eval = (
        PolicyEvaluation.query.filter_by(empresa_id=empresa.id, proveedor_id=proveedor.id)
        .order_by(PolicyEvaluation.creado_en.desc())
        .first()
    )
    versions = (
        PolicyVersion.query.join(PolicySet, PolicySet.id == PolicyVersion.policy_set_id)
        .filter(PolicySet.empresa_id == empresa.id)
        .order_by(PolicyVersion.version.desc())
        .limit(5)
        .all()
    )
    return jsonify(
        {
            "empresa": {
                "id": empresa.id,
                "nombre": empresa.nombre,
                "tipo_empresa": empresa.tipo_empresa,
            },
            "proveedor": {
                "id": proveedor.id,
                "nombre": proveedor.nombre,
                "tipo": proveedor.tipo,
                "nivel": proveedor.nivel,
                "riesgo": {1: "bajo", 2: "medio", 3: "alto", 4: "critico"}.get(proveedor.nivel, "desconocido"),
                "repse": bool(proveedor.repse),
                "tiene_fisico": bool(proveedor.tiene_fisico),
                "efos_ok": bool(proveedor.efos_ok),
            },
            "folio": {
                "id": folio.id,
                "numero": folio.numero,
                "periodo": folio.periodo,
                "presupuesto": folio.presupuesto,
            },
            "policy": {
                "source": "policy_version" if active else "default",
                "version_id": active.id if active else None,
                "version": active.version if active else None,
                "classification": policy.get("classification", {}),
                "gates": policy.get("gates", {}),
                "semaforo": policy.get("semaforo", {}),
            },
            "aplicado": {
                "documentos_requeridos": DOCS_BY_LEVEL.get(proveedor.nivel, []),
                "min_completitud_para_pago": min_comp,
                "completitud_actual": completitud,
                "brecha_completitud": gap,
                "pago_habilitado": (completitud >= min_comp) if exp else False,
                "estado_pago": "liberado" if (completitud >= min_comp and exp) else "bloqueado",
                "documentos_total": docs_total,
                "documentos_validos": docs_ok,
                "documentos_pendientes": docs_pendientes,
                "documentos_observados": docs_observados,
                "reglas_disparadas": clasificacion.get("explicacion", []),
                "clasificacion_calculada": {
                    "nivel": clasificacion.get("nivel"),
                    "riesgo": clasificacion.get("riesgo"),
                    "label": clasificacion.get("label"),
                },
            },
            "auditoria": {
                "ultima_evaluacion": {
                    "id": last_eval.id,
                    "tipo": last_eval.tipo,
                    "creado_en": last_eval.creado_en.isoformat() if last_eval and last_eval.creado_en else None,
                    "policy_version_id": last_eval.policy_version_id,
                }
                if last_eval
                else None,
                "ultimas_versiones_policy": [
                    {
                        "id": v.id,
                        "version": v.version,
                        "estado": v.estado,
                        "creado_por": v.creado_por,
                        "publicado_en": v.publicado_en.isoformat() if v.publicado_en else None,
                        "nota_cambio": v.nota_cambio,
                    }
                    for v in versions
                ],
            },
        }
    )
