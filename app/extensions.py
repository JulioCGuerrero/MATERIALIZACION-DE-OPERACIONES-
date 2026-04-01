"""Registro de extensiones Flask.

La idea es definir los objetos una sola vez aqui y luego inicializarlos
en la fabrica de app (`create_app`) para evitar importaciones circulares.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# `db`: ORM para modelos y consultas SQL.
db = SQLAlchemy()
# `migrate`: soporte de migraciones de esquema de BD.
migrate = Migrate()
# `jwt`: emision y validacion de tokens JWT.
jwt = JWTManager()
