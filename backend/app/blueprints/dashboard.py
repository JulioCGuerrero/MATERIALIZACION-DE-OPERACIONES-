from flask import Blueprint, jsonify, request

from ..models import Alerta, Expediente, Folio, Proveedor, Traspaso
from ..services.semaforo import calcular_semaforo

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    empresa_id = request.args.get("empresa_id", type=int)
    folios_q = Folio.query.filter_by(estado="activo")
    expedientes_q = Expediente.query.join(Expediente.folio)
    traspasos_q = Traspaso.query.join(Traspaso.folio)
    alertas_q = Alerta.query.filter_by(estado="activa")
    if empresa_id:
        folios_q = folios_q.filter(Folio.empresa_id == empresa_id)
        expedientes_q = expedientes_q.filter(Folio.empresa_id == empresa_id)
        traspasos_q = traspasos_q.filter(Folio.empresa_id == empresa_id)
        alertas_q = alertas_q.filter(Alerta.empresa_id == empresa_id)

    folios_activos = folios_q.count()
    materializados = expedientes_q.filter(Expediente.completitud >= 100.0).count()
    pagos_bloqueados = expedientes_q.filter(Expediente.pago_bloqueado.is_(True)).count()
    alertas_ia = traspasos_q.filter((Traspaso.estado == "alerta") | (Traspaso.excede_presup.is_(True))).count()
    alertas_activas = alertas_q.count()

    por_nivel = {
        f"n{nivel}": (
            Proveedor.query.join(Proveedor.folios)
            .filter(Proveedor.nivel == nivel, Proveedor.activo.is_(True), Folio.empresa_id == empresa_id)
            .distinct().count()
            if empresa_id
            else Proveedor.query.filter_by(nivel=nivel, activo=True).count()
        )
        for nivel in range(1, 5)
    }

    return jsonify(
        {
            "folios_activos": folios_activos,
            "materializados": materializados,
            "pagos_bloqueados": pagos_bloqueados,
            "alertas_ia": alertas_ia,
            "alertas_activas": alertas_activas,
            "por_nivel": por_nivel,
            "semaforo": calcular_semaforo(empresa_id=empresa_id),
        }
    )
