from calendar import monthrange
from datetime import date, datetime
import secrets

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Documento, Empresa, Expediente, Folio, Proveedor, ProveedorCredencial
from ..services.auditoria import log_event
from ..services.bloqueo import calcular_completitud
from ..services.catalogo import DOCS_BY_LEVEL
from ..services.clasificador import clasificar_proveedor
from ..services.document_review import aplicar_validacion_documento
from ..services.efos import esta_en_efos, normalizar_rfc
from ..services.onboarding_empresas import empresa_habilitada_para_proveedores
from ..services.policy_engine import get_policy_status
from ..services.serializers import expediente_to_dict

proveedores_bp = Blueprint("proveedores", __name__)


def _next_folio_numero() -> str:
    rows = Folio.query.with_entities(Folio.numero).all()
    nums = []
    for (n,) in rows:
        if isinstance(n, str) and n.isdigit():
            nums.append(int(n))
    base = max(nums) + 1 if nums else 10001
    return str(base)


def _fecha_limite_por_periodo(periodo: str) -> date:
    year, month = [int(x) for x in periodo.split("-")]
    return date(year, month, monthrange(year, month)[1])


def _proveedor_dict(p: Proveedor) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "rfc": p.rfc,
        "tipo": p.tipo,
        "nivel": p.nivel,
        "banco": p.banco,
        "cuenta": p.cuenta,
        "clabe": p.clabe,
        "repse": p.repse,
        "tiene_fisico": p.tiene_fisico,
        "efos_ok": p.efos_ok,
        "activo": p.activo,
        "creado_en": p.creado_en.isoformat() if p.creado_en else None,
    }


def _ensure_proveedor_credencial(proveedor: Proveedor, empresa: Empresa) -> tuple[ProveedorCredencial, bool]:
    cred = ProveedorCredencial.query.filter_by(proveedor_id=proveedor.id, empresa_id=empresa.id).first()
    if cred:
        return cred, False

    username = f"prov_{proveedor.id}_emp_{empresa.id}"
    password = secrets.token_urlsafe(8)
    cred = ProveedorCredencial(
        proveedor_id=proveedor.id,
        empresa_id=empresa.id,
        username=username,
        password=password,
        activo=True,
    )
    db.session.add(cred)
    db.session.flush()
    return cred, True


def _requires_cuestionario_5a(nivel: int) -> bool:
    return nivel in (3, 4)


def _anexar_cuestionario_5a(expediente: Expediente, contenido: str, subido_por: str) -> None:
    doc = next((d for d in expediente.documentos if d.tipo == "cuestionario_5a"), None)
    if not doc:
        doc = Documento(expediente_id=expediente.id, tipo="cuestionario_5a", subido=False)
        db.session.add(doc)
        db.session.flush()

    doc.subido = True
    doc.nombre_archivo = "cuestionario_5a_formulario.txt"
    doc.url = "inline://cuestionario_5a"
    doc.subido_por = subido_por
    doc.validacion_detalle = (contenido or "").strip()
    aplicar_validacion_documento(doc, motor="cuestionario_5a")


@proveedores_bp.get("/proveedores")
def listar_proveedores():
    items = Proveedor.query.order_by(Proveedor.nombre.asc()).all()
    return jsonify([_proveedor_dict(p) for p in items])


@proveedores_bp.get("/proveedores/<int:proveedor_id>")
def obtener_proveedor(proveedor_id: int):
    p = Proveedor.query.get_or_404(proveedor_id)
    return jsonify(_proveedor_dict(p))


@proveedores_bp.post("/proveedores")
def crear_proveedor():
    body = request.get_json(silent=True) or {}
    required = ["nombre", "rfc", "tipo", "monto", "repse", "tiene_fisico"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    rfc = normalizar_rfc(body["rfc"])
    if esta_en_efos(rfc):
        return jsonify({"error": "RFC encontrado en EFOS SAT. Registro bloqueado.", "rfc": rfc}), 409

    empresa = None
    tipo_empresa = (body.get("tipo_empresa") or "servicios").strip().lower()
    if body.get("empresa_id") is not None:
        empresa = Empresa.query.get_or_404(int(body["empresa_id"]))
        tipo_empresa = (empresa.tipo_empresa or tipo_empresa).strip().lower()
        policy_status = get_policy_status(empresa.id)
        if not policy_status.get("has_active_published_policy"):
            return (
                jsonify(
                    {
                        "error": "La empresa no tiene una política activa publicada. Publica la política antes de registrar proveedores.",
                        "empresa_id": empresa.id,
                        "policy_status": policy_status,
                    }
                ),
                409,
            )
        onboarding_ok, onboarding_status = empresa_habilitada_para_proveedores(empresa)
        if not onboarding_ok:
            return (
                jsonify(
                    {
                        "error": "La empresa no tiene onboarding aprobado para recibir proveedores.",
                        "empresa_id": empresa.id,
                        "onboarding_status": onboarding_status,
                    }
                ),
                409,
            )

    clasificado = clasificar_proveedor(
        tipo=body["tipo"],
        monto=float(body["monto"]),
        repse=bool(body["repse"]),
        tiene_fisico=bool(body["tiene_fisico"]),
        tipo_empresa=tipo_empresa,
        empresa_id=empresa.id if empresa else None,
        usuario=body.get("usuario"),
        save_evaluation=True,
    )
    cuestionario_5a = (body.get("cuestionario_5a") or "").strip()
    if empresa is not None and _requires_cuestionario_5a(clasificado["nivel"]) and not cuestionario_5a:
        return (
            jsonify(
                {
                    "error": "Para proveedores nivel 3 o 4 debes capturar el cuestionario 5-A CFF al registrarlo.",
                    "nivel": clasificado["nivel"],
                }
            ),
            400,
        )

    proveedor = Proveedor(
        nombre=body["nombre"],
        rfc=rfc,
        tipo=body["tipo"],
        nivel=clasificado["nivel"],
        banco=body.get("banco"),
        cuenta=body.get("cuenta"),
        clabe=body.get("clabe"),
        repse=bool(body["repse"]),
        tiene_fisico=bool(body["tiene_fisico"]),
        efos_ok=not esta_en_efos(rfc),
        activo=bool(body.get("activo", True)),
    )
    db.session.add(proveedor)
    db.session.flush()
    log_event("proveedores", proveedor.id, "crear", {"nivel": proveedor.nivel}, body.get("usuario"))
    folio_creado = None
    if bool(body.get("crear_folio", False)):
        if "empresa_id" not in body:
            return jsonify({"error": "Para crear folio al registrar proveedor debes enviar empresa_id"}), 400
        if empresa is None:
            empresa = Empresa.query.get_or_404(int(body["empresa_id"]))
        folio = Folio(
            numero=str(body.get("folio_numero") or _next_folio_numero()),
            proveedor_id=proveedor.id,
            empresa_id=empresa.id,
            presupuesto=float(body.get("folio_presupuesto", body.get("monto", 0))),
            periodo=body.get("folio_periodo", "2026-04"),
            fecha_limite_entrega=(
                datetime.strptime(body["fecha_limite_entrega"], "%Y-%m-%d").date()
                if body.get("fecha_limite_entrega")
                else _fecha_limite_por_periodo(body.get("folio_periodo", "2026-04"))
            ),
            estado="activo",
        )
        db.session.add(folio)
        db.session.flush()

        expediente = Expediente(folio_id=folio.id, completitud=0.0, pago_bloqueado=True)
        db.session.add(expediente)
        db.session.flush()

        for tipo_doc in DOCS_BY_LEVEL[proveedor.nivel]:
            db.session.add(Documento(expediente_id=expediente.id, tipo=tipo_doc, subido=False))
        if _requires_cuestionario_5a(proveedor.nivel):
            _anexar_cuestionario_5a(expediente, cuestionario_5a, body.get("usuario") or "sistema")

        folio_creado = {
            "id": folio.id,
            "numero": folio.numero,
            "empresa_id": empresa.id,
            "empresa_nombre": empresa.nombre,
            "periodo": folio.periodo,
            "presupuesto": folio.presupuesto,
            "expediente_id": expediente.id,
        }
        log_event(
            "folios",
            folio.id,
            "crear",
            {"proveedor_id": proveedor.id, "empresa_id": empresa.id, "periodo": folio.periodo},
            body.get("usuario"),
        )

    db.session.commit()
    if folio_creado:
        calcular_completitud(folio_creado["expediente_id"])

    return jsonify({**_proveedor_dict(proveedor), "clasificacion": clasificado, "folio": folio_creado}), 201


@proveedores_bp.patch("/proveedores/<int:proveedor_id>")
def actualizar_proveedor(proveedor_id: int):
    p = Proveedor.query.get_or_404(proveedor_id)
    body = request.get_json(silent=True) or {}

    for field in ["nombre", "rfc", "tipo", "banco", "cuenta", "clabe"]:
        if field in body:
            if field == "rfc":
                value = normalizar_rfc(body[field])
                if esta_en_efos(value):
                    return jsonify({"error": "RFC encontrado en EFOS SAT. Actualización bloqueada.", "rfc": value}), 409
                setattr(p, field, value)
            else:
                setattr(p, field, body[field])

    for field in ["repse", "tiene_fisico", "efos_ok", "activo"]:
        if field in body:
            setattr(p, field, bool(body[field]))

    p.efos_ok = not esta_en_efos(p.rfc)

    if any(k in body for k in ["tipo", "monto", "repse", "tiene_fisico"]):
        monto = float(body.get("monto", 0))
        empresa_tipo = None
        if body.get("empresa_id") is not None:
            emp = Empresa.query.get(int(body["empresa_id"]))
            empresa_tipo = emp.tipo_empresa if emp else None
        clasificado = clasificar_proveedor(
            tipo=p.tipo,
            monto=monto,
            repse=p.repse,
            tiene_fisico=p.tiene_fisico,
            tipo_empresa=(empresa_tipo or body.get("tipo_empresa") or "servicios"),
            empresa_id=int(body["empresa_id"]) if body.get("empresa_id") is not None else None,
            proveedor_id=p.id,
            usuario=body.get("usuario"),
            save_evaluation=True,
        )
    cuestionario_5a = (body.get("cuestionario_5a") or "").strip()
    if _requires_cuestionario_5a(clasificado["nivel"]) and not cuestionario_5a:
        return (
            jsonify(
                {
                    "error": "Para proveedores nivel 3 o 4 debes capturar el cuestionario 5-A CFF al registrarte.",
                    "nivel": clasificado["nivel"],
                }
            ),
            400,
        )
        p.nivel = clasificado["nivel"]

    log_event("proveedores", p.id, "actualizar", body, body.get("usuario"))
    db.session.commit()
    return jsonify(_proveedor_dict(p))


@proveedores_bp.get("/proveedores/<int:proveedor_id>/expedientes")
def expedientes_proveedor(proveedor_id: int):
    Proveedor.query.get_or_404(proveedor_id)
    expedientes = (
        Expediente.query.join(Expediente.folio)
        .filter_by(proveedor_id=proveedor_id)
        .order_by(Expediente.id.desc())
        .all()
    )
    return jsonify([expediente_to_dict(e) for e in expedientes])


@proveedores_bp.post("/proveedores/self-register")
def self_register_proveedor():
    body = request.get_json(silent=True) or {}
    required = ["nombre", "rfc", "tipo", "monto", "repse", "tiene_fisico", "empresa_id"]
    faltantes = [f for f in required if f not in body]
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {', '.join(faltantes)}"}), 400

    rfc = normalizar_rfc(body["rfc"])
    if esta_en_efos(rfc):
        return jsonify({"error": "RFC encontrado en EFOS SAT. Registro bloqueado.", "rfc": rfc}), 409

    empresa = Empresa.query.get_or_404(int(body["empresa_id"]))
    onboarding_ok, onboarding_status = empresa_habilitada_para_proveedores(empresa)
    if not onboarding_ok:
        return (
            jsonify(
                {
                    "error": "La empresa no tiene onboarding aprobado para recibir auto-registro.",
                    "empresa_id": empresa.id,
                    "onboarding_status": onboarding_status,
                }
            ),
            409,
        )
    policy_status = get_policy_status(empresa.id)
    if not policy_status.get("has_active_published_policy"):
        return (
            jsonify(
                {
                    "error": "La empresa no tiene política activa publicada para recibir auto-registro.",
                    "empresa_id": empresa.id,
                    "policy_status": policy_status,
                }
            ),
            409,
        )

    proveedor = Proveedor.query.filter_by(rfc=rfc).first()
    if not proveedor:
        clasificado = clasificar_proveedor(
            tipo=body["tipo"],
            monto=float(body["monto"]),
            repse=bool(body["repse"]),
            tiene_fisico=bool(body["tiene_fisico"]),
            tipo_empresa=(empresa.tipo_empresa or "servicios"),
            empresa_id=empresa.id,
            usuario="proveedor_autoregistro",
            save_evaluation=True,
        )
        proveedor = Proveedor(
            nombre=body["nombre"],
            rfc=rfc,
            tipo=body["tipo"],
            nivel=clasificado["nivel"],
            banco=body.get("banco"),
            cuenta=body.get("cuenta"),
            clabe=body.get("clabe"),
            repse=bool(body["repse"]),
            tiene_fisico=bool(body["tiene_fisico"]),
            efos_ok=True,
            activo=True,
        )
        db.session.add(proveedor)
        db.session.flush()
        log_event("proveedores", proveedor.id, "self_register_crear", {"empresa_id": empresa.id}, "proveedor_autoregistro")
    else:
        clasificado = clasificar_proveedor(
            tipo=proveedor.tipo,
            monto=float(body["monto"]),
            repse=bool(body.get("repse", proveedor.repse)),
            tiene_fisico=bool(body.get("tiene_fisico", proveedor.tiene_fisico)),
            tipo_empresa=(empresa.tipo_empresa or "servicios"),
            empresa_id=empresa.id,
            proveedor_id=proveedor.id,
            usuario="proveedor_autoregistro",
            save_evaluation=True,
        )

    periodo = body.get("folio_periodo", datetime.utcnow().strftime("%Y-%m"))
    folio = Folio.query.filter_by(proveedor_id=proveedor.id, empresa_id=empresa.id, periodo=periodo).first()
    if not folio:
        folio = Folio(
            numero=str(body.get("folio_numero") or _next_folio_numero()),
            proveedor_id=proveedor.id,
            empresa_id=empresa.id,
            presupuesto=float(body.get("folio_presupuesto", body.get("monto", 0))),
            periodo=periodo,
            fecha_limite_entrega=(
                datetime.strptime(body["fecha_limite_entrega"], "%Y-%m-%d").date()
                if body.get("fecha_limite_entrega")
                else _fecha_limite_por_periodo(periodo)
            ),
            estado="activo",
        )
        db.session.add(folio)
        db.session.flush()
        expediente = Expediente(folio_id=folio.id, completitud=0.0, pago_bloqueado=True)
        db.session.add(expediente)
        db.session.flush()
        for tipo_doc in DOCS_BY_LEVEL[proveedor.nivel]:
            db.session.add(Documento(expediente_id=expediente.id, tipo=tipo_doc, subido=False))
        if _requires_cuestionario_5a(proveedor.nivel):
            _anexar_cuestionario_5a(expediente, cuestionario_5a, "proveedor_autoregistro")
        log_event(
            "folios",
            folio.id,
            "self_register_crear",
            {"proveedor_id": proveedor.id, "empresa_id": empresa.id, "periodo": folio.periodo},
            "proveedor_autoregistro",
        )
    elif folio and folio.expediente and _requires_cuestionario_5a(proveedor.nivel):
        _anexar_cuestionario_5a(folio.expediente, cuestionario_5a, "proveedor_autoregistro")

    cred, is_new_cred = _ensure_proveedor_credencial(proveedor, empresa)
    db.session.commit()
    if folio and folio.expediente:
        calcular_completitud(folio.expediente.id)

    return (
        jsonify(
            {
                "ok": True,
                "proveedor": _proveedor_dict(proveedor),
                "folio": {
                    "id": folio.id,
                    "numero": folio.numero,
                    "empresa_id": empresa.id,
                    "empresa_nombre": empresa.nombre,
                    "periodo": folio.periodo,
                    "expediente_id": folio.expediente.id if folio.expediente else None,
                },
                "credenciales": {
                    "username": cred.username,
                    "password": cred.password,
                    "empresa_id": empresa.id,
                    "empresa_nombre": empresa.nombre,
                    "proveedor_id": proveedor.id,
                    "proveedor_nombre": proveedor.nombre,
                    "es_nueva": is_new_cred,
                },
                "clasificacion": clasificado,
            }
        ),
        201,
    )
