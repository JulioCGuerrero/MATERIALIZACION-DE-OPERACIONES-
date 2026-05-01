from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Documento, Expediente
from ..services.auditoria import log_event
from ..services.bloqueo import calcular_completitud
from ..services.document_review import aplicar_validacion_documento
from ..services.serializers import doc_to_dict

documentos_bp = Blueprint("documentos", __name__)


@documentos_bp.get("/documentos/<int:expediente_id>")
def documentos_expediente(expediente_id: int):
    expediente = Expediente.query.get_or_404(expediente_id)
    return jsonify([doc_to_dict(d) for d in expediente.documentos])


@documentos_bp.post("/documentos/<int:documento_id>/subir")
def subir_documento(documento_id: int):
    doc = Documento.query.get_or_404(documento_id)
    body = request.get_json(silent=True) or {}
    uploaded = request.files.get("archivo")

    if uploaded:
        filename = secure_filename(uploaded.filename or f"{doc.tipo}.bin")
        upload_dir = Path(current_app.config["BASE_DIR"]) / "uploads" / str(doc.expediente_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        uploaded.save(file_path)
        body["nombre_archivo"] = filename
        body["url"] = f"/uploads/{doc.expediente_id}/{filename}"
        if not body.get("subido_por"):
            body["subido_por"] = request.form.get("subido_por", "frontend")

    doc.subido = True
    doc.subido_en = datetime.utcnow()
    doc.nombre_archivo = body.get("nombre_archivo")
    doc.url = body.get("url")
    doc.subido_por = body.get("subido_por")

    if doc.tipo == "manifiesto_materialidad":
        doc.expediente.manifiesto = True

    validacion = aplicar_validacion_documento(doc)

    log_event("documentos", doc.id, "actualizar", {"tipo": doc.tipo, "subido": True}, body.get("subido_por"))
    log_event(
        "documentos",
        doc.id,
        "validacion_automatica",
        {"tipo": doc.tipo, "estado": validacion["estado"], "detalle": validacion["detalle"]},
        "motor_validacion",
    )
    db.session.commit()

    completitud = calcular_completitud(doc.expediente_id)
    return jsonify({"documento": doc_to_dict(doc), "completitud": completitud})
