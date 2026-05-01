from datetime import datetime
from io import BytesIO
import json
import zipfile

from flask import Blueprint, jsonify, make_response, request

from ..models import AuditLog
from ..services.pdf_reports import PdfEngineMissing, render_pdf
from ..services.reportes import (
    reporte_por_nivel_data,
    reporte_semaforo_data,
    reporte_trazabilidad_data,
)

export_bp = Blueprint("export", __name__)


def _pdf_response(content: bytes, filename: str):
    response = make_response(content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@export_bp.get("/export/reportes/nivel.pdf")
def export_nivel_pdf():
    nivel = request.args.get("nivel", type=int)
    empresa_id = request.args.get("empresa_id", type=int)
    data = reporte_por_nivel_data(nivel, empresa_id)
    try:
        pdf = render_pdf("reports/niveles.html", report=data, nivel=nivel)
    except PdfEngineMissing as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Error al generar PDF de niveles: {exc}"}), 500
    name = f"reporte_nivel_{nivel}.pdf" if nivel else "reporte_niveles.pdf"
    return _pdf_response(pdf, name)


@export_bp.get("/export/reportes/semaforo.pdf")
def export_semaforo_pdf():
    data = reporte_semaforo_data()
    try:
        pdf = render_pdf("reports/semaforo.html", semaforo=data)
    except PdfEngineMissing as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Error al generar PDF de semáforo: {exc}"}), 500
    return _pdf_response(pdf, "reporte_semaforo_fiscal.pdf")


@export_bp.get("/export/reportes/trazabilidad.pdf")
def export_trazabilidad_pdf():
    empresa_id = request.args.get("empresa_id", type=int)
    data = reporte_trazabilidad_data(empresa_id)
    try:
        pdf = render_pdf("reports/trazabilidad.html", report=data)
    except PdfEngineMissing as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Error al generar PDF de trazabilidad: {exc}"}), 500
    return _pdf_response(pdf, "reporte_trazabilidad_bancaria.pdf")


@export_bp.get("/export/reportes/auditoria.pdf")
def export_auditoria_pdf():
    rows = AuditLog.query.order_by(AuditLog.creado_en.desc()).limit(400).all()
    items = [
        {
            "tabla": r.tabla,
            "tabla_id": r.tabla_id,
            "accion": r.accion,
            "detalle": r.detalle,
            "usuario": r.usuario,
            "creado_en": r.creado_en.strftime("%Y-%m-%d %H:%M") if r.creado_en else "",
        }
        for r in rows
    ]
    try:
        pdf = render_pdf("reports/auditoria.html", items=items)
    except PdfEngineMissing as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Error al generar PDF de auditoría: {exc}"}), 500
    return _pdf_response(pdf, "reporte_auditoria_ia.pdf")


@export_bp.get("/export/paquete_sat.zip")
def export_paquete_sat_zip():
    empresa_id = request.args.get("empresa_id", type=int)
    nivel = reporte_por_nivel_data(empresa_id=empresa_id)
    semaforo = reporte_semaforo_data()
    trazabilidad = reporte_trazabilidad_data(empresa_id)
    rows = AuditLog.query.order_by(AuditLog.creado_en.desc()).limit(400).all()
    audit_items = [
        {
            "tabla": r.tabla,
            "tabla_id": r.tabla_id,
            "accion": r.accion,
            "detalle": r.detalle,
            "usuario": r.usuario,
            "creado_en": r.creado_en.strftime("%Y-%m-%d %H:%M") if r.creado_en else "",
        }
        for r in rows
    ]

    try:
        pdf_niveles = render_pdf("reports/niveles.html", report=nivel, nivel=None)
        pdf_semaforo = render_pdf("reports/semaforo.html", semaforo=semaforo)
        pdf_trazabilidad = render_pdf("reports/trazabilidad.html", report=trazabilidad)
        pdf_auditoria = render_pdf("reports/auditoria.html", items=audit_items)
    except PdfEngineMissing as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Error al generar paquete SAT: {exc}"}), 500

    payload = {
        "generado_en": datetime.now().isoformat(),
        "semaforo": semaforo,
        "niveles": nivel,
        "trazabilidad": trazabilidad,
        "audit_log": audit_items,
    }

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("01_reporte_niveles.pdf", pdf_niveles)
        zf.writestr("02_reporte_semaforo_fiscal.pdf", pdf_semaforo)
        zf.writestr("03_reporte_trazabilidad_bancaria.pdf", pdf_trazabilidad)
        zf.writestr("04_reporte_auditoria_ia.pdf", pdf_auditoria)
        zf.writestr("05_paquete_sat_datos.json", json.dumps(payload, ensure_ascii=False, indent=2))

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/zip"
    response.headers["Content-Disposition"] = 'attachment; filename="paquete_sat.zip"'
    return response
