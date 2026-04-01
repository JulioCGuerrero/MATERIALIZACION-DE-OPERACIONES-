from flask import Flask

from app.config import Config
from app.extensions import db, migrate, jwt
from app.auth import auth_bp
from app.main import main_bp
from app.folios import folios_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(folios_bp, url_prefix="/folios")

    @app.context_processor
    def inject_globals():
        return {"company_name": app.config.get("COMPANY_NAME", "Batia")}

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app
