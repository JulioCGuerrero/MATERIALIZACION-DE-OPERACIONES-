from flask import Blueprint, jsonify, request

from ..models import Usuario

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


@auth_bp.get("/auth/usuarios")
def usuarios_demo():
    rows = Usuario.query.filter_by(activo=True).order_by(Usuario.rol.asc(), Usuario.nombre.asc()).all()
    return jsonify([_user_dict(u) for u in rows])
