from flask import Flask, send_from_directory
from flask_cors import CORS

from .blueprints.audit_log import audit_log_bp
from .blueprints.alertas import alertas_bp
from .blueprints.clasificador import clasificador_bp
from .blueprints.conciliacion import conciliacion_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.documentos import documentos_bp
from .blueprints.empresas import empresas_bp
from .blueprints.efos import efos_bp
from .blueprints.expedientes import expedientes_bp
from .blueprints.export import export_bp
from .blueprints.folios import folios_bp
from .blueprints.proveedores import proveedores_bp
from .blueprints.reportes import reportes_bp
from .blueprints.semaforo import semaforo_bp
from .blueprints.traspasos import traspasos_bp
from .config import Config
from .extensions import db


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(proveedores_bp, url_prefix="/api")
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
    app.register_blueprint(reportes_bp, url_prefix="/api")
    app.register_blueprint(conciliacion_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")

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
