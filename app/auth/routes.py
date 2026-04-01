from functools import wraps

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_jwt_extended import create_access_token

from app.audit import log_action
from app.auth import auth_bp
from app.models import User


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped


def roles_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            role = session.get("role")
            if role not in allowed_roles:
                flash("No tienes permisos para acceder a esta sección.", "error")
                return redirect(url_for("main.dashboard"))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, is_active=True).first()

        if not user or not user.check_password(password):
            flash("Credenciales inválidas", "error")
            log_action(
                user_id=None,
                action="login_failed",
                entity="auth",
                details=f"email={email}",
            )
            return render_template("auth/login.html"), 401

        session["user_id"] = user.id
        session["user_name"] = user.full_name
        session["role"] = user.role.name

        log_action(
            user_id=user.id,
            action="login_success",
            entity="auth",
            details=f"role={user.role.name}",
        )
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    user_id = session.get("user_id")
    session.clear()
    log_action(user_id=user_id, action="logout", entity="auth")
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/token", methods=["POST"])
def token():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Credenciales inválidas"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role.name, "name": user.full_name},
    )
    log_action(user_id=user.id, action="jwt_issued", entity="auth")
    return jsonify({"access_token": access_token})
