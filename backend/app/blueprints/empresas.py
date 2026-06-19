from datetime import datetime
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Empresa, EmpresaCuentaBancaria, EmpresaDocumento, Folio
from ..security import get_actor
from ..services.auditoria import log_event
from ..services.empresa_credentials import ensure_empresa_credencial
from ..services.onboarding_empresas import (
    DOCS_REQUERIDOS_EMPRESA,
    REGLAS_NEGOCIO_REQUERIDAS,
    empresa_onboarding_status,
)
from ..services.policy_engine import get_policy_status
from ..services.serializers import expediente_to_dict
from ..services.storage import delete_object_url, save_upload

empresas_bp = Blueprint("empresas", __name__)
TIPOS_EMPRESA = {
    "servicios",
    "comercializadora",
    "industrial",
    "constructora",
    "logistica",
    "tecnologia",
    "financiera",
    "otra",
}


def _empresa_dict(e: Empresa) -> dict:
    return {
        "id": e.id,
        "nombre": e.nombre,
        "rfc": e.rfc,
        "tipo_empresa": e.tipo_empresa,
        "activo": e.activo,
        "onboarding_status": e.onboarding_status,
        "onboarding_aprobada_en": e.onboarding_aprobada_en.isoformat() if e.onboarding_aprobada_en else None,
        "onboarding_aprobada_por": e.onboarding_aprobada_por,
        "creado_en": e.creado_en.isoformat() if e.creado_en else None,
    }


def _empresa_cred_dict(username: str, password: str, empresa: Empresa) -> dict:
    return {
        "username": username,
        "password": password,
        "empresa_id": empresa.id,
        "empresa_nombre": empresa.nombre,
    }


def _contabilidad_bank_only_response():
    return jsonify({"error": "El rol contabilidad solo puede gestionar estados de cuenta y cuentas bancarias de empresas ya existentes."}), 403


def _actor_is_contabilidad() -> bool:
    actor = get_actor()
    return bool(actor and actor.is_internal and actor.role == "contabilidad")


def _portal_empresa_payload(empresa: Empresa) -> dict:
    folios = Folio.query.filter_by(empresa_id=empresa.id).order_by(Folio.creado_en.desc()).all()
    expedientes = [expediente_to_dict(f.expediente) for f in folios if f.expediente]

    proveedores = []
    seen = set()
    for folio in folios:
        proveedor = folio.proveedor
        if not proveedor or proveedor.id in seen:
            continue
        seen.add(proveedor.id)
        prov_folios = [f for f in folios if f.proveedor_id == proveedor.id]
        docs_total = sum(len(f.expediente.documentos) for f in prov_folios if f.expediente)
        docs_ok = sum(
            1
            for f in prov_folios
            if f.expediente
            for d in f.expediente.documentos
            if d.subido
        )
        proveedores.append(
            {
                "id": proveedor.id,
                "nombre": proveedor.nombre,
                "rfc": proveedor.rfc,
                "tipo": proveedor.tipo,
                "nivel": proveedor.nivel,
                "activo": proveedor.activo,
                "folios": [
                    {
                        "id": f.id,
                        "numero": f.numero,
                        "periodo": f.periodo,
                        "presupuesto": f.presupuesto,
                        "estado": f.estado,
                        "expediente_id": f.expediente.id if f.expediente else None,
                        "completitud": f.expediente.completitud if f.expediente else 0.0,
                        "pago_bloqueado": f.expediente.pago_bloqueado if f.expediente else True,
                    }
                    for f in prov_folios
                ],
                "documentos_subidos": docs_ok,
                "documentos_total": docs_total,
            }
        )

    return {
        "empresa": _empresa_dict(empresa),
        "policy_status": get_policy_status(empresa.id),
        "onboarding_status": empresa_onboarding_status(empresa),
        "documentos_empresa": [
            {
                "id": d.id,
                "tipo": d.tipo,
                "nombre_archivo": d.nombre_archivo,
                "url": d.url,
                "estado_validacion": d.estado_validacion,
                "subido_en": d.subido_en.isoformat() if d.subido_en else None,
            }
            for d in empresa.documentos
        ],
        "cuentas_bancarias": [_cuenta_dict(c) for c in empresa.cuentas_bancarias],
        "proveedores": proveedores,
        "expedientes": expedientes,
    }


def _cuenta_dict(c: EmpresaCuentaBancaria) -> dict:
    return {
        "id": c.id,
        "banco": c.banco,
        "titular": c.titular,
        "clabe": c.clabe,
        "numero_cuenta": c.numero_cuenta,
        "moneda": c.moneda,
        "activa": c.activa,
        "validada": c.validada,
        "validada_por": c.validada_por,
        "validada_en": c.validada_en.isoformat() if c.validada_en else None,
        "creada_en": c.creada_en.isoformat() if c.creada_en else None,
    }


@empresas_bp.get("/empresas")
def listar_empresas():
    items = Empresa.query.order_by(Empresa.nombre.asc()).all()
    return jsonify([_empresa_dict(e) for e in items])


@empresas_bp.post("/empresas")
def crear_empresa():
    body = request.get_json(silent=True) or {}
    required = ["nombre", "rfc"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    tipo_empresa = (body.get("tipo_empresa") or "servicios").strip().lower()
    if tipo_empresa not in TIPOS_EMPRESA:
        return jsonify({"error": f"tipo_empresa inválido. Valores permitidos: {', '.join(sorted(TIPOS_EMPRESA))}"}), 400

    empresa = Empresa(
        nombre=body["nombre"].strip(),
        rfc=body["rfc"].strip().upper(),
        tipo_empresa=tipo_empresa,
        activo=bool(body.get("activo", True)),
        onboarding_status=body.get("onboarding_status", "borrador"),
        reglas_negocio={k: bool(body.get("reglas_negocio", {}).get(k, False)) for k in REGLAS_NEGOCIO_REQUERIDAS},
    )
    db.session.add(empresa)
    db.session.flush()
    cred, _ = ensure_empresa_credencial(empresa)
    log_event("empresas", empresa.id, "crear", {"rfc": empresa.rfc}, body.get("usuario"))
    db.session.commit()
    return jsonify({**_empresa_dict(empresa), "credenciales": _empresa_cred_dict(cred.username, cred.password, empresa)}), 201


@empresas_bp.patch("/empresas/<int:empresa_id>")
def actualizar_empresa(empresa_id: int):
    if _actor_is_contabilidad():
        return _contabilidad_bank_only_response()
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}

    if "nombre" in body:
        nombre = (body.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"error": "nombre no puede estar vacío"}), 400
        empresa.nombre = nombre

    if "rfc" in body:
        rfc = (body.get("rfc") or "").strip().upper()
        if not rfc:
            return jsonify({"error": "rfc no puede estar vacío"}), 400
        empresa.rfc = rfc

    if "tipo_empresa" in body:
        tipo_empresa = (body.get("tipo_empresa") or "").strip().lower()
        if tipo_empresa not in TIPOS_EMPRESA:
            return jsonify({"error": f"tipo_empresa inválido. Valores permitidos: {', '.join(sorted(TIPOS_EMPRESA))}"}), 400
        empresa.tipo_empresa = tipo_empresa

    log_event(
        "empresas",
        empresa.id,
        "actualizar",
        {"nombre": empresa.nombre, "rfc": empresa.rfc, "tipo_empresa": empresa.tipo_empresa},
        body.get("usuario"),
    )
    db.session.commit()
    return jsonify(_empresa_dict(empresa))


@empresas_bp.get("/empresas/<int:empresa_id>/onboarding/status")
def onboarding_status_empresa(empresa_id: int):
    empresa = Empresa.query.get_or_404(empresa_id)
    return jsonify(empresa_onboarding_status(empresa))


@empresas_bp.get("/empresas/catalogo/onboarding")
def onboarding_catalogo():
    return jsonify(
        {
            "documentos_requeridos": DOCS_REQUERIDOS_EMPRESA,
            "reglas_negocio_requeridas": REGLAS_NEGOCIO_REQUERIDAS,
        }
    )


@empresas_bp.get("/portal-empresa/resumen")
def portal_empresa_resumen():
    actor = get_actor()
    empresa_id = request.args.get("empresa_id", type=int)
    if actor and actor.is_internal and actor.role == "administracion":
        empresa = Empresa.query.get_or_404(empresa_id) if empresa_id else Empresa.query.order_by(Empresa.nombre.asc()).first_or_404()
        return jsonify(_portal_empresa_payload(empresa))

    empresa = Empresa.query.get_or_404(actor.empresa_id)
    return jsonify(_portal_empresa_payload(empresa))


@empresas_bp.post("/empresas/<int:empresa_id>/documentos")
def subir_documento_empresa(empresa_id: int):
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    uploaded = request.files.get("archivo")
    if uploaded:
        body = request.form.to_dict()
    required = ["tipo", "nombre_archivo"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400
    tipo = (body.get("tipo") or "").strip()
    if tipo not in DOCS_REQUERIDOS_EMPRESA:
        return jsonify({"error": "tipo de documento no permitido para onboarding"}), 400
    if _actor_is_contabilidad() and tipo != "estado_cuenta_bancario":
        return _contabilidad_bank_only_response()

    doc = EmpresaDocumento.query.filter_by(empresa_id=empresa.id, tipo=tipo).first()
    previous_url = doc.url if doc else None
    if not doc:
        doc = EmpresaDocumento(empresa_id=empresa.id, tipo=tipo)
        db.session.add(doc)

    if uploaded:
        filename = secure_filename(uploaded.filename or body.get("nombre_archivo") or f"{tipo}.bin")
        body["url"] = save_upload(uploaded, f"empresas/{empresa.id}/{filename}")
        body["nombre_archivo"] = filename
        if not body.get("usuario"):
            body["usuario"] = request.form.get("usuario", "frontend")

    doc.nombre_archivo = (body.get("nombre_archivo") or "").strip()
    doc.url = body.get("url")
    doc.subido_por = body.get("usuario")
    doc.subido_en = datetime.utcnow()
    doc.estado_validacion = "pendiente"
    doc.observaciones = None
    if body.get("vigente_hasta"):
        doc.vigente_hasta = datetime.strptime(body["vigente_hasta"], "%Y-%m-%d").date()

    if previous_url and previous_url != doc.url:
        delete_object_url(previous_url)

    log_event("empresas", empresa.id, "onboarding_documento_subir", {"tipo": tipo}, body.get("usuario"))
    db.session.commit()
    return jsonify({"ok": True, "empresa_id": empresa.id, "documento_id": doc.id}), 201


@empresas_bp.patch("/empresas/<int:empresa_id>/documentos/<int:doc_id>/validar")
def validar_documento_empresa(empresa_id: int, doc_id: int):
    Empresa.query.get_or_404(empresa_id)
    doc = EmpresaDocumento.query.filter_by(id=doc_id, empresa_id=empresa_id).first_or_404()
    if _actor_is_contabilidad() and doc.tipo != "estado_cuenta_bancario":
        return _contabilidad_bank_only_response()
    body = request.get_json(silent=True) or {}
    estado = (body.get("estado_validacion") or "").strip().lower()
    if estado not in {"valido", "observado", "rechazado"}:
        return jsonify({"error": "estado_validacion inválido"}), 400
    doc.estado_validacion = estado
    doc.observaciones = body.get("observaciones")
    doc.validado_por = body.get("usuario")
    doc.validado_en = datetime.utcnow()
    log_event(
        "empresas",
        empresa_id,
        "onboarding_documento_validar",
        {"documento_id": doc.id, "estado_validacion": estado},
        body.get("usuario"),
    )
    db.session.commit()
    return jsonify({"ok": True})


@empresas_bp.post("/empresas/<int:empresa_id>/cuentas-bancarias")
def crear_cuenta_bancaria_empresa(empresa_id: int):
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    required = ["banco", "titular", "clabe"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    cuenta = EmpresaCuentaBancaria(
        empresa_id=empresa.id,
        banco=(body.get("banco") or "").strip(),
        titular=(body.get("titular") or "").strip(),
        clabe=(body.get("clabe") or "").strip(),
        numero_cuenta=(body.get("numero_cuenta") or "").strip() or None,
        moneda=(body.get("moneda") or "MXN").strip().upper(),
        activa=bool(body.get("activa", True)),
        validada=bool(body.get("validada", False)),
    )
    if cuenta.validada:
        cuenta.validada_por = body.get("usuario")
        cuenta.validada_en = datetime.utcnow()

    db.session.add(cuenta)
    log_event("empresas", empresa.id, "onboarding_cuenta_crear", {"clabe": cuenta.clabe}, body.get("usuario"))
    db.session.commit()
    return jsonify({"ok": True, "cuenta_id": cuenta.id}), 201


@empresas_bp.get("/empresas/<int:empresa_id>/cuentas-bancarias")
def listar_cuentas_bancarias_empresa(empresa_id: int):
    Empresa.query.get_or_404(empresa_id)
    cuentas = EmpresaCuentaBancaria.query.filter_by(empresa_id=empresa_id).order_by(EmpresaCuentaBancaria.creada_en.desc()).all()
    return jsonify([_cuenta_dict(c) for c in cuentas])


@empresas_bp.patch("/empresas/<int:empresa_id>/cuentas-bancarias/<int:cuenta_id>")
def actualizar_cuenta_bancaria_empresa(empresa_id: int, cuenta_id: int):
    Empresa.query.get_or_404(empresa_id)
    cuenta = EmpresaCuentaBancaria.query.filter_by(id=cuenta_id, empresa_id=empresa_id).first_or_404()
    body = request.get_json(silent=True) or {}

    for field in ["banco", "titular", "clabe", "numero_cuenta", "moneda"]:
        if field in body:
            setattr(cuenta, field, body[field].strip() if isinstance(body[field], str) else body[field])
    if "activa" in body:
        cuenta.activa = bool(body["activa"])
    if "validada" in body:
        cuenta.validada = bool(body["validada"])
        cuenta.validada_por = body.get("usuario")
        cuenta.validada_en = datetime.utcnow() if cuenta.validada else None

    log_event("empresas", empresa_id, "onboarding_cuenta_actualizar", {"cuenta_id": cuenta.id}, body.get("usuario"))
    db.session.commit()
    return jsonify({"ok": True})


@empresas_bp.patch("/empresas/<int:empresa_id>/reglas-negocio")
def actualizar_reglas_negocio(empresa_id: int):
    if _actor_is_contabilidad():
        return _contabilidad_bank_only_response()
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    reglas = empresa.reglas_negocio or {}
    for regla in REGLAS_NEGOCIO_REQUERIDAS:
        if regla in body:
            reglas[regla] = bool(body[regla])
    empresa.reglas_negocio = reglas
    log_event("empresas", empresa.id, "onboarding_reglas_actualizar", reglas, body.get("usuario"))
    db.session.commit()
    return jsonify({"ok": True, "reglas_negocio": empresa.reglas_negocio})


@empresas_bp.post("/empresas/<int:empresa_id>/onboarding/enviar-revision")
def enviar_revision_onboarding(empresa_id: int):
    if _actor_is_contabilidad():
        return _contabilidad_bank_only_response()
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    empresa.onboarding_status = "en_revision"
    log_event("empresas", empresa.id, "onboarding_enviar_revision", {}, body.get("usuario"))
    db.session.commit()
    return jsonify({"ok": True, "onboarding_status": empresa.onboarding_status})


@empresas_bp.post("/empresas/<int:empresa_id>/onboarding/aprobar")
def aprobar_onboarding(empresa_id: int):
    if _actor_is_contabilidad():
        return _contabilidad_bank_only_response()
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    status = empresa_onboarding_status(empresa)
    if not status["puede_aprobarse"]:
        return jsonify({"error": "Checklist incompleto para aprobar onboarding", "status": status}), 409
    empresa.onboarding_status = "aprobada"
    empresa.onboarding_aprobada_en = datetime.utcnow()
    empresa.onboarding_aprobada_por = body.get("usuario")
    log_event("empresas", empresa.id, "onboarding_aprobar", status, body.get("usuario"))
    db.session.commit()
    return jsonify({"ok": True, "onboarding_status": empresa.onboarding_status})


@empresas_bp.post("/empresas/<int:empresa_id>/onboarding/rechazar")
def rechazar_onboarding(empresa_id: int):
    empresa = Empresa.query.get_or_404(empresa_id)
    body = request.get_json(silent=True) or {}
    empresa.onboarding_status = "rechazada"
    log_event(
        "empresas",
        empresa.id,
        "onboarding_rechazar",
        {"motivo": body.get("motivo")},
        body.get("usuario"),
    )
    db.session.commit()
    return jsonify({"ok": True, "onboarding_status": empresa.onboarding_status})
