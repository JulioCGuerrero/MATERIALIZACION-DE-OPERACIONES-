from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import EmpresaCredencial, ProveedorCredencial, Usuario
from ..services.empresa_credentials import ensure_all_empresa_credenciales_demo
from ..security import get_actor, issue_auth_token

auth_bp = Blueprint("auth", __name__)

DEMO_INTERNAL_PASSWORDS = {
    "salo@batia.local": "DirBatia#2026",
    "mgonzalez@batia.local": "TesoMgonz#2026",
    "lhernandez@batia.local": "TesoLhern#2026",
    "rfuentes@batia.local": "AdminRfuen#2026",
    "cmorales@batia.local": "AdminCmora#2026",
    "pramirez@batia.local": "ContaPram#2026",
}


def _user_dict(u: Usuario) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "nombre": u.nombre,
        "rol": u.rol,
        "activo": u.activo,
    }


def ensure_demo_internal_passwords() -> int:
    updated = 0
    for email, password in DEMO_INTERNAL_PASSWORDS.items():
        user = Usuario.query.filter_by(email=email, activo=True).first()
        if not user:
            continue
        if user.password == password:
            continue
        user.password = password
        updated += 1
    if updated:
        db.session.commit()
    return updated


@auth_bp.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Debes enviar email y password"}), 400

    ensure_demo_internal_passwords()
    user = Usuario.query.filter_by(email=email, activo=True).first()
    if not user or user.password != password:
        return jsonify({"error": "Credenciales inválidas"}), 401

    return jsonify({"ok": True, "usuario": _user_dict(user), "token": issue_auth_token("internal", user.email)})


@auth_bp.post("/auth/proveedor/login")
def login_proveedor():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Debes enviar username y password"}), 400

    cred = ProveedorCredencial.query.filter_by(username=username, activo=True).first()
    if not cred or cred.password != password:
        return jsonify({"error": "Credenciales inválidas"}), 401

    proveedor = cred.proveedor
    empresa = cred.empresa
    return jsonify(
        {
            "ok": True,
            "token": issue_auth_token("proveedor", cred.username),
            "usuario": {
                "tipo": "proveedor",
                "username": cred.username,
                "rol": "proveedor",
                "proveedor_id": cred.proveedor_id,
                "proveedor_nombre": proveedor.nombre if proveedor else None,
                "empresa_id": cred.empresa_id,
                "empresa_nombre": empresa.nombre if empresa else None,
                "cliente_nombre": (empresa.cliente_nombre or empresa.nombre) if empresa else None,
                "activo": cred.activo,
            },
        }
    )


@auth_bp.post("/auth/empresa/login")
def login_empresa():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Debes enviar username y password"}), 400

    db.create_all()
    ensure_all_empresa_credenciales_demo()
    cred = EmpresaCredencial.query.filter_by(username=username, activo=True).first()
    if not cred or cred.password != password:
        return jsonify({"error": "Credenciales inválidas"}), 401

    empresa = cred.empresa
    return jsonify(
        {
            "ok": True,
            "token": issue_auth_token("empresa", cred.username),
            "usuario": {
                "tipo": "empresa_cliente",
                "username": cred.username,
                "rol": "empresa_cliente",
                "empresa_id": cred.empresa_id,
                "empresa_nombre": empresa.nombre if empresa else None,
                "activo": cred.activo,
            },
        }
    )


@auth_bp.get("/auth/usuarios")
def usuarios_demo():
    rows = Usuario.query.filter_by(activo=True).order_by(Usuario.rol.asc(), Usuario.nombre.asc()).all()
    return jsonify([_user_dict(u) for u in rows])


@auth_bp.get("/auth/me")
def auth_me():
    actor = get_actor()
    if not actor:
        return jsonify({"autenticado": False})
    return jsonify(
        {
            "autenticado": True,
            "actor_type": actor.actor_type,
            "rol": actor.role,
            "email": actor.email,
            "user_id": actor.user_id,
            "nombre": actor.nombre,
            "proveedor_id": actor.proveedor_id,
            "empresa_id": actor.empresa_id,
            "username": actor.username,
        }
    )
