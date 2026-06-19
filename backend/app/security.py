from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .extensions import db
from flask import current_app, g, request

from .models import EmpresaCredencial, ProveedorCredencial, Usuario
from .services.empresa_credentials import ensure_all_empresa_credenciales_demo

INTERNAL_ROLES = {"direccion", "tesoreria", "administracion", "contabilidad"}
AUDITORIA_IA_ROLES = {"direccion", "tesoreria", "contabilidad"}
ADMIN_ONLY_CREATION_PATHS = {
    "/api/empresas",
    "/api/proveedores",
}


@dataclass
class AuthActor:
    actor_type: str
    role: str
    email: str | None = None
    user_id: int | None = None
    nombre: str | None = None
    proveedor_id: int | None = None
    empresa_id: int | None = None
    username: str | None = None

    @property
    def is_internal(self) -> bool:
        return self.actor_type == "internal"

    @property
    def is_proveedor(self) -> bool:
        return self.actor_type == "proveedor"

    @property
    def is_empresa(self) -> bool:
        return self.actor_type == "empresa"


def _path() -> str:
    return request.path or ""


def _is_public_request() -> bool:
    path = _path()
    method = request.method.upper()
    if not path.startswith("/api/"):
        return True
    if path in {"/api/health", "/api/auth/login", "/api/auth/proveedor/login", "/api/auth/empresa/login", "/api/auth/usuarios"}:
        return True
    if method == "GET" and path == "/api/empresas":
        return True
    if method == "GET" and path == "/api/folios":
        return True
    if method == "GET" and path.startswith("/api/empresas/") and path.endswith("/policy/status"):
        return True
    if method == "GET" and path.startswith("/api/empresas/") and path.endswith("/onboarding/status"):
        return True
    if method == "GET" and path.startswith("/api/efos/consultar"):
        return True
    if method == "POST" and path == "/api/proveedores/self-register":
        return True
    return False


def _is_auditoria_ia_path(path: str) -> bool:
    return path in {
        "/api/audit_log",
        "/api/conciliacion/estado_cuenta",
        "/api/export/reportes/nivel.pdf",
        "/api/export/reportes/semaforo.pdf",
        "/api/export/reportes/auditoria.pdf",
        "/api/export/reportes/trazabilidad.pdf",
        "/api/export/paquete_sat.zip",
    }


def _ensure_empresa_credenciales_table() -> None:
    inspector = inspect(db.engine)
    if "empresa_credenciales" not in set(inspector.get_table_names()):
        db.create_all()


def issue_auth_token(actor_type: str, subject: str) -> str:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="servicia-auth-v1")
    return serializer.dumps({"actor_type": actor_type, "subject": subject})


def _token_identity() -> tuple[str, str] | None:
    authorization = (request.headers.get("Authorization") or "").strip()
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    try:
        payload = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"], salt="servicia-auth-v1"
        ).loads(token, max_age=current_app.config.get("AUTH_TOKEN_MAX_AGE", 28800))
    except (BadSignature, SignatureExpired):
        return None
    actor_type = str(payload.get("actor_type") or "")
    subject = str(payload.get("subject") or "")
    return (actor_type, subject) if actor_type and subject else None


def _load_internal_actor(email: str | None = None) -> AuthActor | None:
    email = (email or request.headers.get("X-Auth-Email") or "").strip().lower()
    role = (request.headers.get("X-Auth-Role") or "").strip().lower()
    if email and not role:
        user = Usuario.query.filter_by(email=email, activo=True).first()
        role = (user.rol or "").strip().lower() if user else ""
    if not email or role not in INTERNAL_ROLES:
        return None
    user = Usuario.query.filter_by(email=email, activo=True).first()
    if not user or (user.rol or "").strip().lower() != role:
        return None
    return AuthActor(
        actor_type="internal",
        role=role,
        email=user.email,
        user_id=user.id,
        nombre=user.nombre,
    )


def _load_proveedor_actor(username: str | None = None) -> AuthActor | None:
    username = (username or request.headers.get("X-Proveedor-Username") or "").strip()
    if not username:
        return None
    cred = ProveedorCredencial.query.filter_by(username=username, activo=True).first()
    if not cred:
        return None
    return AuthActor(
        actor_type="proveedor",
        role="proveedor",
        proveedor_id=cred.proveedor_id,
        empresa_id=cred.empresa_id,
        username=cred.username,
        nombre=cred.proveedor.nombre if cred.proveedor else cred.username,
    )


def _load_empresa_actor(username: str | None = None) -> AuthActor | None:
    username = (username or request.headers.get("X-Empresa-Username") or "").strip()
    if not username:
        return None
    _ensure_empresa_credenciales_table()
    ensure_all_empresa_credenciales_demo()
    cred = EmpresaCredencial.query.filter_by(username=username, activo=True).first()
    if not cred:
        return None
    return AuthActor(
        actor_type="empresa",
        role="empresa_cliente",
        empresa_id=cred.empresa_id,
        username=cred.username,
        nombre=cred.empresa.nombre if cred.empresa else cred.username,
    )


def get_actor() -> AuthActor | None:
    actor = getattr(g, "auth_actor", None)
    if actor is not None:
        return actor
    identity = _token_identity()
    actor = None
    if identity:
        actor_type, subject = identity
        loaders = {
            "internal": _load_internal_actor,
            "proveedor": _load_proveedor_actor,
            "empresa": _load_empresa_actor,
        }
        loader = loaders.get(actor_type)
        actor = loader(subject) if loader else None
    elif current_app.config.get("TESTING") or current_app.config.get("ALLOW_LEGACY_AUTH_HEADERS"):
        actor = _load_internal_actor() or _load_proveedor_actor() or _load_empresa_actor()
    g.auth_actor = actor
    return actor


def is_allowed(actor: AuthActor, method: str, path: str) -> bool:
    method = method.upper()

    if actor.is_proveedor:
        if method == "GET" and path in {"/api/auth/me"}:
            return True
        if method == "POST" and path == "/api/clasificar":
            return True
        if method == "GET" and (path == "/api/folios" or path.startswith("/api/folios/")):
            return True
        if method == "GET" and (path == "/api/expedientes" or path.startswith("/api/expedientes/")):
            return True
        if (method == "GET" and path.startswith("/api/documentos/")) or (
            method == "POST" and path.startswith("/api/documentos/") and path.endswith("/subir")
        ):
            return True
        return False

    if actor.is_empresa:
        if method == "GET" and path in {"/api/auth/me", "/api/portal-empresa/resumen"}:
            return True
        return False

    role = actor.role
    if method == "POST" and path in ADMIN_ONLY_CREATION_PATHS:
        return role == "administracion"
    if method == "POST" and path.startswith("/api/empresas/") and path.endswith("/policy/upload"):
        return role == "administracion"

    if _is_auditoria_ia_path(path):
        if role not in AUDITORIA_IA_ROLES:
            return False
        if method == "GET":
            return True
        return method == "POST" and path == "/api/conciliacion/estado_cuenta"

    if role == "direccion":
        return True

    if role == "tesoreria":
        if method == "GET":
            return True
        if method == "POST" and (path == "/api/traspasos" or path == "/api/conciliacion/estado_cuenta"):
            return True
        if method == "PATCH" and path.startswith("/api/alertas/") and path.endswith("/resolver"):
            return True
        return False

    if role == "administracion":
        if method == "GET":
            return True
        if method == "POST" and path in {"/api/documentos", "/api/proveedores", "/api/folios", "/api/empresas"}:
            return True
        if method == "POST" and path.startswith("/api/empresas/") and path.endswith("/policy/upload"):
            return True
        if method == "POST" and (
            (path.startswith("/api/empresas/") and path.endswith("/documentos"))
            or (path.startswith("/api/empresas/") and path.endswith("/cuentas-bancarias"))
            or (path.startswith("/api/empresas/") and path.endswith("/onboarding/enviar-revision"))
            or (path.startswith("/api/empresas/") and path.endswith("/onboarding/aprobar"))
        ):
            return True
        if method == "POST" and path.startswith("/api/documentos/") and path.endswith("/subir"):
            return True
        if method == "PATCH" and (
            path.startswith("/api/proveedores/")
            or path.startswith("/api/folios/")
            or path.startswith("/api/empresas/")
        ):
            return True
        return False

    if role == "contabilidad":
        return True

    return False


def check_request_access() -> tuple[bool, str, int]:
    if current_app.config.get("TESTING"):
        return True, "", 200
    if _is_public_request():
        return True, "", 200
    actor = get_actor()
    if not actor:
        return False, "Debes autenticarte para usar este endpoint", 401
    if not is_allowed(actor, request.method, _path()):
        return False, f"Rol '{actor.role}' sin permiso para esta operación", 403
    return True, "", 200
