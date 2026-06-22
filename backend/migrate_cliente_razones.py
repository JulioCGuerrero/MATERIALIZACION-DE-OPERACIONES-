"""Agrega la agrupación cliente -> razones sociales sin borrar datos."""

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db


app = create_app()

with app.app_context():
    columns = {column["name"] for column in inspect(db.engine).get_columns("empresas")}
    if "cliente_nombre" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE empresas ADD COLUMN cliente_nombre TEXT NOT NULL DEFAULT 'Sin cliente'")
            )

    with db.engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE empresas
                SET cliente_nombre = CASE
                    WHEN lower(nombre) IN ('batia', 'grupo_batia') THEN 'Grupo Batia'
                    ELSE nombre
                END
                WHERE cliente_nombre IS NULL
                   OR trim(cliente_nombre) = ''
                   OR cliente_nombre = 'Sin cliente'
                """
            )
        )

    print("Migración cliente/razones sociales aplicada correctamente")
