"""Punto de entrada de la aplicacion en desarrollo.

Este archivo:
1) crea la app Flask con la fabrica `create_app`,
2) carga datos demo (seed) dentro del contexto de app,
3) levanta el servidor local.
"""

from app import create_app
from app.seed import seed_data

# Creamos una unica instancia de la app para usarla en `flask run` o `python run.py`.
app = create_app()

if __name__ == "__main__":
    # El contexto de aplicacion permite acceder a BD/configuracion global.
    with app.app_context():
        # Seed idempotente: si ya existen datos base, no los duplica.
        seed_data()
    # Servidor local de desarrollo.
    app.run(host="127.0.0.1", port=5000, debug=True)
