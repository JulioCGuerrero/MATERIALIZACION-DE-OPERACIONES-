"""Rutas del modulo principal (landing + dashboard)."""

from flask import render_template, session

from app.auth.routes import login_required
from app.main import main_bp
from app.models import AuditLog, Folio, MonthlyDirectionReport, ReconciliationAlert


@main_bp.route("/")
def home():
    """Si el usuario ya esta autenticado, lo manda al dashboard.

    Si no hay sesion, muestra la landing publica.
    """
    if session.get("user_id"):
        return dashboard()
    return render_template("landing.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Construye indicadores ejecutivos para pintar el dashboard."""
    # Folios activos (no cerrados).
    active_count = Folio.query.filter(Folio.status.in_(["pendiente", "en_proceso", "alerta", "critico"]))\
        .count()
    # Folios completados.
    closed_count = Folio.query.filter_by(status="cerrado").count()
    # Folios con riesgo alto.
    critical_count = Folio.query.filter(Folio.status.in_(["alerta", "critico"]))\
        .count()
    # Eventos historicos de auditoria.
    audit_count = AuditLog.query.count()
    # Alertas operativas aun abiertas.
    open_alerts = ReconciliationAlert.query.filter_by(status="abierta").count()
    # Reportes mensuales registrados.
    report_count = MonthlyDirectionReport.query.count()

    return render_template(
        "dashboard.html",
        active_count=active_count,
        closed_count=closed_count,
        critical_count=critical_count,
        audit_count=audit_count,
        open_alerts=open_alerts,
        report_count=report_count,
    )
