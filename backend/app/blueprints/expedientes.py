from flask import Blueprint, jsonify, request

from ..models import Expediente, Folio, Proveedor
from ..services.bloqueo import calcular_completitud, puede_pagar
from ..services.serializers import expediente_to_dict

expedientes_bp = Blueprint("expedientes", __name__)


@expedientes_bp.get("/expedientes")
def listar_expedientes():
    q = Expediente.query.join(Expediente.folio).join(Folio.proveedor)

    if request.args.get("bloqueado"):
        bloqueado = request.args["bloqueado"].lower() in ("1", "true", "si")
        q = q.filter(Expediente.pago_bloqueado == bloqueado)

    if request.args.get("nivel"):
        nivel = int(request.args["nivel"])
        q = q.filter(Proveedor.nivel == nivel)

    if request.args.get("proveedor_id"):
        q = q.filter(Folio.proveedor_id == int(request.args["proveedor_id"]))
    if request.args.get("empresa_id"):
        q = q.filter(Folio.empresa_id == int(request.args["empresa_id"]))

    items = q.order_by(Expediente.id.desc()).all()
    return jsonify([expediente_to_dict(e) for e in items])


@expedientes_bp.get("/expedientes/<int:expediente_id>")
def detalle_expediente(expediente_id: int):
    calcular_completitud(expediente_id)
    exp = Expediente.query.get_or_404(expediente_id)
    return jsonify(expediente_to_dict(exp))


@expedientes_bp.get("/expedientes/<int:expediente_id>/completitud")
def completitud_expediente(expediente_id: int):
    data = puede_pagar(expediente_id)
    return jsonify(data)
