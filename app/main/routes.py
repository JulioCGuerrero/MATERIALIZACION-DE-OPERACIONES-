"""Rutas del modulo principal (landing, dashboard y busqueda global)."""

from datetime import datetime, timedelta, timezone

from flask import render_template, request, session
from sqlalchemy import func, or_

from app.auth.routes import login_required
from app.main import main_bp
from app.models import (
    AuditLog,
    CfdiRecord,
    Folio,
    FolioDeliverableItem,
    MonthlyDirectionReport,
    Provider,
    ReconciliationAlert,
    SignatureAck,
    Transfer,
)


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
    # Distribucion por estatus para bloque directivo.
    status_distribution = {
        "pendiente": Folio.query.filter_by(status="pendiente").count(),
        "en_proceso": Folio.query.filter_by(status="en_proceso").count(),
        "listo_para_cierre": Folio.query.filter_by(status="listo_para_cierre").count(),
        "cerrado": closed_count,
        "alerta": Folio.query.filter_by(status="alerta").count(),
        "critico": Folio.query.filter_by(status="critico").count(),
    }
    # Top proveedores con folios activos para enfocar seguimiento.
    top_providers = (
        Provider.query
        .join(Folio, Folio.provider_id == Provider.id)
        .filter(Folio.status.in_(["pendiente", "en_proceso", "alerta", "critico"]))
        .all()
    )
    provider_counter = {}
    for provider in top_providers:
        provider_counter[provider.name] = provider_counter.get(provider.name, 0) + 1
    top_provider_rows = sorted(
        [{"name": name, "active_folios": count} for name, count in provider_counter.items()],
        key=lambda row: row["active_folios"],
        reverse=True,
    )[:5]

    recent_reports = MonthlyDirectionReport.query.order_by(MonthlyDirectionReport.created_at.desc()).limit(3).all()
    report_snapshots = [
        {
            "period": report.period,
            "summary": (report.executive_summary or "")[:120],
            "created_at": report.created_at,
        }
        for report in recent_reports
    ]
    current_role = session.get("role", "")

    pending_ui_items = FolioDeliverableItem.query.filter_by(owner_area="ui", uploaded=False).count()
    pending_contab_items = FolioDeliverableItem.query.filter_by(owner_area="contabilidad", uploaded=False).count()
    folios_without_transfer = (
        Folio.query.outerjoin(Transfer, Transfer.folio_id == Folio.id)
        .filter(Folio.status.in_(["pendiente", "en_proceso", "alerta", "critico"]))
        .group_by(Folio.id)
        .having(func.count(Transfer.id) == 0)
        .count()
    )
    folios_without_cfdi = (
        Folio.query.outerjoin(CfdiRecord, (CfdiRecord.folio_id == Folio.id) & (CfdiRecord.status == "vigente"))
        .filter(Folio.status.in_(["en_proceso", "alerta", "critico"]))
        .group_by(Folio.id)
        .having(func.count(CfdiRecord.id) == 0)
        .count()
    )
    open_alerts_old = ReconciliationAlert.query.filter(
        ReconciliationAlert.status == "abierta",
        ReconciliationAlert.created_at <= (datetime.now(timezone.utc) - timedelta(days=5)),
    ).count()
    signed_areas = SignatureAck.query.count()
    role_focus = {
        "ui": [
            {"label": "Entregables UI pendientes", "value": pending_ui_items},
            {"label": "Folios activos", "value": active_count},
            {"label": "Folios criticos", "value": critical_count},
        ],
        "contabilidad": [
            {"label": "Entregables contables pendientes", "value": pending_contab_items},
            {"label": "Alertas abiertas", "value": open_alerts},
            {"label": "Folios sin CFDI vigente", "value": folios_without_cfdi},
        ],
        "tesoreria": [
            {"label": "Folios por traspasar", "value": folios_without_transfer},
            {"label": "Alertas de alto riesgo", "value": ReconciliationAlert.query.filter_by(status="abierta", severity="alta").count()},
            {"label": "Folios activos", "value": active_count},
        ],
        "direccion": [
            {"label": "Reportes emitidos", "value": report_count},
            {"label": "Alertas abiertas >5 dias", "value": open_alerts_old},
            {"label": "Areas con acuse firmado", "value": signed_areas},
        ],
    }.get(current_role, [])
    role_actions = {
        "ui": [
            {"name": "Abrir folios", "href": "folios.list_folios"},
            {"name": "Panel de operacion", "href": "operations.index"},
            {"name": "Buscador global", "href": "main.global_search"},
        ],
        "contabilidad": [
            {"name": "Centro de alertas", "href": "operations.alerts_center"},
            {"name": "Cumplimiento SAT", "href": "operations.compliance"},
            {"name": "Conciliacion IA", "href": "operations.reconciliation"},
        ],
        "tesoreria": [
            {"name": "Registrar traspasos", "href": "operations.transfers"},
            {"name": "Consultar alertas", "href": "operations.alerts_center"},
            {"name": "Buscador global", "href": "main.global_search"},
        ],
        "direccion": [
            {"name": "Reportes ejecutivos", "href": "operations.reports"},
            {"name": "Centro de alertas", "href": "operations.alerts_center"},
            {"name": "Buscador global", "href": "main.global_search"},
        ],
    }.get(current_role, [])

    return render_template(
        "dashboard.html",
        active_count=active_count,
        closed_count=closed_count,
        critical_count=critical_count,
        audit_count=audit_count,
        open_alerts=open_alerts,
        report_count=report_count,
        status_distribution=status_distribution,
        top_provider_rows=top_provider_rows,
        report_snapshots=report_snapshots,
        current_role=current_role,
        role_focus=role_focus,
        role_actions=role_actions,
        pending_ui_items=pending_ui_items,
        pending_contab_items=pending_contab_items,
        folios_without_transfer=folios_without_transfer,
        folios_without_cfdi=folios_without_cfdi,
        open_alerts_old=open_alerts_old,
        signed_areas=signed_areas,
    )


@main_bp.route("/busqueda")
@login_required
def global_search():
    """Buscador global para navegar por folios, proveedor, UUID CFDI y SPEI."""
    q = request.args.get("q", "").strip()
    query_term = f"%{q}%"
    folios = []
    providers = []
    cfdis = []
    transfers = []
    alerts = []

    if q:
        folios = (
            Folio.query.join(Provider)
            .filter(
                or_(
                    Folio.singa_number.ilike(query_term),
                    Folio.communication_responsible.ilike(query_term),
                    Provider.name.ilike(query_term),
                )
            )
            .order_by(Folio.created_at.desc())
            .limit(25)
            .all()
        )
        providers = Provider.query.filter(Provider.name.ilike(query_term)).order_by(Provider.name.asc()).limit(15).all()
        cfdis = CfdiRecord.query.filter(CfdiRecord.uuid.ilike(query_term)).order_by(CfdiRecord.created_at.desc()).limit(15).all()
        transfers = Transfer.query.filter(Transfer.spei_reference.ilike(query_term)).order_by(Transfer.created_at.desc()).limit(15).all()
        alerts = (
            ReconciliationAlert.query.join(Folio, Folio.id == ReconciliationAlert.folio_id, isouter=True)
            .filter(
                or_(
                    ReconciliationAlert.alert_type.ilike(query_term),
                    ReconciliationAlert.notes.ilike(query_term),
                    Folio.singa_number.ilike(query_term),
                )
            )
            .order_by(ReconciliationAlert.created_at.desc())
            .limit(20)
            .all()
        )

    return render_template(
        "operations/search.html",
        q=q,
        folios=folios,
        providers=providers,
        cfdis=cfdis,
        transfers=transfers,
        alerts=alerts,
    )
