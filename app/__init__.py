"""Inicializacion principal de Flask.

Aqui se conectan:
- configuracion global,
- extensiones (DB, migraciones, JWT),
- blueprints (modulos/rutas),
- y algunos hooks comunes de seguridad/contexto.
"""

import os

from flask import Flask

from app.config import Config
from app.extensions import db, migrate, jwt
from app.auth import auth_bp
from app.main import main_bp
from app.folios import folios_bp
from app.operations import operations_bp


def create_app(config_class=Config):
    """Fabrica de app (patron recomendado en Flask).

    Usar fabrica permite crear app en distintos contextos:
    tests, desarrollo, produccion, scripts, etc.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Carpeta donde se guardan archivos subidos por usuarios.
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Inicializacion de extensiones.
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Registro de modulos de rutas.
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(folios_bp, url_prefix="/folios")
    app.register_blueprint(operations_bp, url_prefix="/operacion")

    @app.context_processor
    def inject_globals():
        # Variables disponibles automaticamente en todas las plantillas Jinja.
        return {"company_name": app.config.get("COMPANY_NAME", "Batia")}

    @app.after_request
    def add_security_headers(response):
        # Headers basicos de hardening para UI web.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app
