from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect, text

from .blueprints.audit_log import audit_log_bp
from .blueprints.alertas import alertas_bp
from .blueprints.automation import automation_bp
from .blueprints.auth import auth_bp
from .blueprints.clasificador import clasificador_bp
from .blueprints.conciliacion import conciliacion_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.documentos import documentos_bp
from .blueprints.empresas import empresas_bp
from .blueprints.efos import efos_bp
from .blueprints.expedientes import expedientes_bp
from .blueprints.export import export_bp
from .blueprints.folios import folios_bp
from .blueprints.kpis import kpis_bp
from .blueprints.policies import policies_bp
from .blueprints.proveedores import proveedores_bp
from .blueprints.reportes import reportes_bp
from .blueprints.semaforo import semaforo_bp
from .blueprints.traspasos import traspasos_bp
from .config import Config
from .extensions import db
from .security import check_request_access


def _create_schema(app: Flask) -> None:
    with app.app_context():
        from . import models  # noqa: F401

        engine = db.engine
        if engine.dialect.name == "postgresql":
            with engine.begin() as connection:
                connection.execute(text("SELECT pg_advisory_lock(4393188)"))
                try:
                    for table_name in db.metadata.tables:
                        sequence_name = f"{table_name}_id_seq"
                        row = connection.execute(
                            text("SELECT to_regclass(:table_name), to_regclass(:sequence_name)"),
                            {"table_name": table_name, "sequence_name": sequence_name},
                        ).one()
                        if row[0] is None and row[1] is not None:
                            connection.execute(text(f'DROP SEQUENCE IF EXISTS "{sequence_name}" CASCADE'))
                    db.metadata.create_all(bind=connection)
                    _ensure_runtime_columns(connection, dialect="postgresql")
                finally:
                    connection.execute(text("SELECT pg_advisory_unlock(4393188)"))
            return

        db.create_all()
        with engine.begin() as connection:
            _ensure_runtime_columns(connection, dialect=engine.dialect.name)


def _ensure_runtime_columns(connection, dialect: str) -> None:
    inspector = inspect(connection)
    existing = {c["name"] for c in inspector.get_columns("empresas")}
    wanted = (
        {
            "onboarding_status": "TEXT NOT NULL DEFAULT 'borrador'",
            "onboarding_aprobada_en": "TIMESTAMP",
            "onboarding_aprobada_por": "TEXT",
            "reglas_negocio": "JSONB DEFAULT '{}'::jsonb",
        }
        if dialect == "postgresql"
        else {
            "onboarding_status": "TEXT NOT NULL DEFAULT 'borrador'",
            "onboarding_aprobada_en": "TIMESTAMP",
            "onboarding_aprobada_por": "TEXT",
            "reglas_negocio": "TEXT DEFAULT '{}'",
        }
    )
    for col, col_type in wanted.items():
        if col in existing:
            continue
        if dialect == "postgresql":
            connection.execute(text(f'ALTER TABLE empresas ADD COLUMN IF NOT EXISTS "{col}" {col_type}'))
        else:
            connection.execute(text(f"ALTER TABLE empresas ADD COLUMN {col} {col_type}"))


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(proveedores_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(efos_bp, url_prefix="/api")
    app.register_blueprint(clasificador_bp, url_prefix="/api")
    app.register_blueprint(folios_bp, url_prefix="/api")
    app.register_blueprint(expedientes_bp, url_prefix="/api")
    app.register_blueprint(documentos_bp, url_prefix="/api")
    app.register_blueprint(empresas_bp, url_prefix="/api")
    app.register_blueprint(traspasos_bp, url_prefix="/api")
    app.register_blueprint(semaforo_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(audit_log_bp, url_prefix="/api")
    app.register_blueprint(alertas_bp, url_prefix="/api")
    app.register_blueprint(automation_bp, url_prefix="/api")
    app.register_blueprint(reportes_bp, url_prefix="/api")
    app.register_blueprint(kpis_bp, url_prefix="/api")
    app.register_blueprint(conciliacion_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")
    app.register_blueprint(policies_bp, url_prefix="/api")

    if app.config.get("AUTO_CREATE_SCHEMA"):
        _create_schema(app)

    @app.before_request
    def _authz_guard():
        allowed, message, status = check_request_access()
        if not allowed:
            return jsonify({"error": message}), status

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/")
    def index():
        return send_from_directory(str(app.config["BASE_DIR"]), "frontend.html")

    @app.get("/uploads/<path:filename>")
    def uploads(filename: str):
        return send_from_directory(str(app.config["BASE_DIR"] / "uploads"), filename)

    return app
