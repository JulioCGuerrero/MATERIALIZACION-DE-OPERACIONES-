"""Servicios de negocio para flujo operativo de folios.

Este modulo concentra reglas reutilizables (fechas limite, checklist,
recalculo de workflow/estatus) para que las rutas no queden saturadas.
"""

from datetime import date, datetime, timedelta, timezone

from app.models import FolioDeliverableItem, FolioWorkflow, ReconciliationAlert

# Entregables base de UI que aplican a todos los tipos de proveedor.
BASE_UI_DELIVERABLES = [
    ("oc_firmada", "Orden de compra firmada y aprobada"),
    ("contrato_vigente", "Contrato o acuerdo de servicio vigente"),
    ("responsable_comunicacion", "Nombre y cargo del responsable de comunicacion"),
    ("comunicaciones_formales", "Correos o comunicaciones formales relevantes"),
]

# Entregables especificos segun tipo de proveedor.
TYPE_UI_DELIVERABLES = {
    "outsourcing": [
        ("lista_personal", "Lista de personal asignado por sitio"),
        ("turnos_horarios", "Turnos y horarios documentados"),
        ("asistencias", "Listas de asistencia firmadas"),
        ("bitacoras", "Bitacoras operativas firmadas"),
        ("fotos_servicio", "Evidencia fotografica del servicio"),
        ("supervision", "Supervision documentada"),
    ],
    "materiales": [
        ("fotos_materiales", "Fotos de materiales recibidos"),
        ("acuse_recepcion", "Acuse de recepcion firmado"),
        ("inventario", "Registro de inventario actualizado"),
        ("evidencia_entrega", "Evidencia de entrega al cliente o sitio"),
    ],
    "servicios": [
        ("procesos_operados", "Definicion de procesos operados"),
        ("reportes_kpi", "Reportes de operacion con KPI"),
        ("evidencia_intervencion", "Logs, tickets y reportes de trabajo"),
        ("resultados_documentados", "Resultados documentados y SLAs"),
        ("acta_entrega", "Acta de entrega-recepcion mensual o por hito"),
    ],
}

# Entregables de contabilidad.
CONTAB_DELIVERABLES = [
    ("opinion_sat", "Opinion de cumplimiento SAT vigente"),
    ("revision_efos", "Revision EFOS sin hallazgos"),
    ("cfdi_xml_pdf", "CFDI vinculado (XML y PDF)"),
    ("conciliacion_mensual", "Conciliacion Banco-CFDI-Contabilidad"),
]

# `weekday()` usa: Lunes=0 ... Domingo=6.
WEEKEND = {5, 6}


def add_business_days(base_date, business_days):
    """Suma dias habiles (saltando sabado y domingo)."""
    current = base_date
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() not in WEEKEND:
            added += 1
    return current


def month_cutoff(day):
    """Devuelve una fecha de corte dentro del mes actual."""
    today = date.today()
    return date(today.year, today.month, day)


def due_date_for_code(code, owner_area):
    """Calcula fecha limite por tipo de entregable (reglas del proceso)."""
    if code in {"oc_firmada", "contrato_vigente"}:
        return add_business_days(date.today(), 2)
    if code in {"asistencias", "fotos_servicio", "bitacoras", "inventario", "evidencia_entrega"}:
        return add_business_days(date.today(), 5)
    if code == "comunicaciones_formales":
        return month_cutoff(25)
    if code in {"opinion_sat", "revision_efos"}:
        return add_business_days(date.today(), 1)
    if code == "cfdi_xml_pdf":
        return add_business_days(date.today(), 3)
    if code == "conciliacion_mensual":
        return month_cutoff(30)
    return add_business_days(date.today(), 5 if owner_area == "ui" else 3)


def kpi_status_for_item(item):
    """Estado KPI simple para UI: completo / vencido / pendiente."""
    if item.uploaded:
        return "completo"
    if item.due_date and item.due_date < date.today():
        return "vencido"
    return "pendiente"


def ensure_workflow(folio):
    """Obtiene el workflow del folio o lo crea si no existe."""
    workflow = FolioWorkflow.query.filter_by(folio_id=folio.id).first()
    if workflow:
        return workflow
    return FolioWorkflow(folio_id=folio.id, step_1_ui_folio=True)


def ensure_deliverables(folio):
    """Genera entregables faltantes para el folio indicado.

    La funcion usa `yield` para devolver items uno por uno.
    """
    existing_codes = {item.code for item in FolioDeliverableItem.query.filter_by(folio_id=folio.id).all()}

    full_list = []
    full_list.extend(BASE_UI_DELIVERABLES)
    full_list.extend(TYPE_UI_DELIVERABLES.get(folio.provider_type, []))

    for code, name in full_list:
        if code not in existing_codes:
            yield FolioDeliverableItem(
                folio_id=folio.id,
                code=code,
                name=name,
                owner_area="ui",
                due_date=due_date_for_code(code, "ui"),
            )

    for code, name in CONTAB_DELIVERABLES:
        if code not in existing_codes:
            yield FolioDeliverableItem(
                folio_id=folio.id,
                code=code,
                name=name,
                owner_area="contabilidad",
                due_date=due_date_for_code(code, "contabilidad"),
            )


def recalculate_workflow_from_data(folio, workflow, deliverables, has_transfer, has_cfdi, has_reconciliation):
    """Recalcula los 8 pasos del flujo segun datos actuales."""
    ui_items = [d for d in deliverables if d.owner_area == "ui"]
    contab_items = [d for d in deliverables if d.owner_area == "contabilidad"]

    workflow.step_3_ui_deliverables = bool(ui_items) and all(d.uploaded for d in ui_items)
    workflow.step_2_contab_sat = all(
        d.uploaded for d in contab_items if d.code in {"opinion_sat", "revision_efos"}
    ) and any(d.code == "opinion_sat" for d in contab_items)
    workflow.step_4_tesoreria_transfer = has_transfer and workflow.step_2_contab_sat
    workflow.step_5_contab_cfdi = has_cfdi and workflow.step_4_tesoreria_transfer
    workflow.step_6_contab_reconciliation = has_reconciliation and workflow.step_5_contab_cfdi
    workflow.step_7_ui_ready_to_close = workflow.step_3_ui_deliverables and workflow.step_6_contab_reconciliation
    workflow.step_8_contab_closed = workflow.step_7_ui_ready_to_close and workflow.step_6_contab_reconciliation
    workflow.updated_at = datetime.now(timezone.utc)


def evaluate_folio_status(folio, workflow):
    """Asigna estatus semaforo al folio segun flujo y alertas."""
    open_high_alerts = ReconciliationAlert.query.filter_by(folio_id=folio.id, status="abierta", severity="alta").count()

    if open_high_alerts > 0:
        folio.status = "critico"
    elif workflow.step_8_contab_closed:
        folio.status = "cerrado"
    elif workflow.step_7_ui_ready_to_close and workflow.step_6_contab_reconciliation:
        folio.status = "listo_para_cierre"
    elif workflow.step_3_ui_deliverables or workflow.step_4_tesoreria_transfer or workflow.step_5_contab_cfdi:
        folio.status = "en_proceso"
    else:
        folio.status = "pendiente"


def update_folio_operational_status(*, folio, workflow, deliverables, has_transfer, has_cfdi, has_reconciliation):
    """Funcion fachada: recalcula workflow y luego estatus del folio."""
    recalculate_workflow_from_data(
        folio,
        workflow,
        deliverables,
        has_transfer,
        has_cfdi,
        has_reconciliation,
    )
    evaluate_folio_status(folio, workflow)
