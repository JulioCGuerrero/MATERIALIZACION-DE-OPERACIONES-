from flask import Blueprint, jsonify, request

from ..models import ProveedorCredencial, Usuario
from ..security import get_actor

auth_bp = Blueprint("auth", __name__)


def _user_dict(u: Usuario) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "nombre": u.nombre,
        "rol": u.rol,
        "activo": u.activo,
    }


@auth_bp.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Debes enviar email y password"}), 400

    user = Usuario.query.filter_by(email=email, activo=True).first()
    if not user or user.password != password:
        return jsonify({"error": "Credenciales inválidas"}), 401

    return jsonify({"ok": True, "usuario": _user_dict(user)})


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
            "usuario": {
                "tipo": "proveedor",
                "username": cred.username,
                "rol": "proveedor",
                "proveedor_id": cred.proveedor_id,
                "proveedor_nombre": proveedor.nombre if proveedor else None,
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
