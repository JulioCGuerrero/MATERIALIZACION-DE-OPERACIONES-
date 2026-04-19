from flask import Blueprint, jsonify

from ..models import Expediente, Folio, Proveedor, Traspaso
from ..services.semaforo import calcular_semaforo

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    folios_activos = Folio.query.filter_by(estado="activo").count()
    materializados = Expediente.query.filter(Expediente.completitud >= 100.0).count()
    pagos_bloqueados = Expediente.query.filter_by(pago_bloqueado=True).count()
    alertas_ia = Traspaso.query.filter((Traspaso.estado == "alerta") | (Traspaso.excede_presup.is_(True))).count()

    por_nivel = {
        "n1": Proveedor.query.filter_by(nivel=1, activo=True).count(),
        "n2": Proveedor.query.filter_by(nivel=2, activo=True).count(),
        "n3": Proveedor.query.filter_by(nivel=3, activo=True).count(),
        "n4": Proveedor.query.filter_by(nivel=4, activo=True).count(),
    }

    return jsonify(
        {
            "folios_activos": folios_activos,
            "materializados": materializados,
            "pagos_bloqueados": pagos_bloqueados,
            "alertas_ia": alertas_ia,
            "por_nivel": por_nivel,
            "semaforo": calcular_semaforo(),
        }
    )
