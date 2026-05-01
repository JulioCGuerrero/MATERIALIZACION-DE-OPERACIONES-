from datetime import datetime

from app import create_app
from app.services.automation import ejecutar_automatizacion

app = create_app()


if __name__ == "__main__":
    with app.app_context():
        periodo = datetime.now().strftime("%Y-%m")
        result = ejecutar_automatizacion(periodo=periodo, usuario="cron_auto")
        print(result)
