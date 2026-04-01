from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from app.audit import log_action
from app.auth.routes import login_required, roles_required
from app.extensions import db
from app.folios import folios_bp
from app.models import AuditLog, AuthorizedAccount, Folio, Provider
from app.operations.services import ensure_deliverables, ensure_workflow


ALLOWED_CREATOR_ROLES = {"ui", "direccion"}
ALLOWED_STATUS_UPDATE_ROLES = {"ui", "contabilidad", "direccion"}
ALLOWED_FOLIO_STATUSES = {"pendiente", "en_proceso", "listo_para_cierre", "cerrado", "alerta", "critico"}


def _build_folio_query():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    provider_type = request.args.get("provider_type", "").strip()

    query = Folio.query.join(Provider)

    if q:
        like_term = f"%{q}%"
        query = query.filter(
            or_(
                Folio.singa_number.ilike(like_term),
                Provider.name.ilike(like_term),
                Folio.communication_responsible.ilike(like_term),
            )
        )

    if status:
        query = query.filter(Folio.status == status)

    if provider_type:
        query = query.filter(Folio.provider_type == provider_type)

    return query, {"q": q, "status": status, "provider_type": provider_type}


def _render_folios_page(*, status_code=200, form_data=None):
    query, filters = _build_folio_query()
    items = query.order_by(Folio.created_at.desc()).all()
    providers = Provider.query.order_by(Provider.name.asc()).all()
    tab = request.args.get("tab", "resumen").strip().lower()
    if tab not in {"resumen", "alta", "historial"}:
        tab = "resumen"
    current_query = request.query_string.decode("utf-8")

    status_counts = {k: 0 for k in ALLOWED_FOLIO_STATUSES}
    for folio in items:
        status_counts[folio.status] = status_counts.get(folio.status, 0) + 1

    recent_audits = (
        AuditLog.query.filter_by(entity="folio")
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "folios/list.html",
        folios=items,
        providers=providers,
        filters=filters,
        result_count=len(items),
        can_create=session.get("role") in ALLOWED_CREATOR_ROLES,
        form_data=form_data or {},
        tab=tab,
        current_query=current_query,
        status_counts=status_counts,
        recent_audits=recent_audits,
    ), status_code


@folios_bp.route("/", methods=["GET", "POST"])
@login_required
def list_folios():
    if request.method == "GET":
        return _render_folios_page()

    if session.get("role") not in ALLOWED_CREATOR_ROLES:
        flash("No tienes permisos para crear folios.", "error")
        return _render_folios_page(status_code=403)

    singa_number = request.form.get("singa_number", "").strip()
    provider_id = request.form.get("provider_id")
    responsible = request.form.get("communication_responsible", "").strip()
    budget_amount = request.form.get("budget_amount", "0").strip()
    contract_amount = request.form.get("contract_amount", "0").strip()

    form_data = {
        "singa_number": singa_number,
        "provider_id": provider_id or "",
        "communication_responsible": responsible,
        "budget_amount": budget_amount,
        "contract_amount": contract_amount,
    }

    if not singa_number:
        flash("El numero de folio SINGA es obligatorio.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    provider = Provider.query.get(int(provider_id)) if provider_id else None
    if not provider:
        flash("Proveedor invalido.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    has_authorized_account = AuthorizedAccount.query.filter_by(provider_id=provider.id, is_active=True).count() > 0
    if not has_authorized_account:
        flash("Bloqueo duro: no se puede crear un folio con proveedor sin cuenta autorizada.", "error")
        log_action(
            user_id=session.get("user_id"),
            action="folio_creation_blocked",
            entity="folio",
            details=f"provider={provider.name};reason=no_authorized_account",
        )
        return _render_folios_page(status_code=400, form_data=form_data)

    try:
        budget_decimal = Decimal(budget_amount)
        contract_decimal = Decimal(contract_amount)
    except InvalidOperation:
        flash("Montos invalidos. Verifica los campos numericos.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    if budget_decimal <= 0:
        flash("El presupuesto autorizado debe ser mayor a cero.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    if contract_decimal <= 0:
        flash("El monto de contrato debe ser mayor a cero.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    if budget_decimal > contract_decimal:
        flash("El presupuesto SINGA no puede exceder el monto del contrato.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    try:
        folio = Folio(
            singa_number=singa_number,
            provider_id=provider.id,
            provider_type=provider.provider_type,
            communication_responsible=responsible,
            contract_amount=contract_decimal,
            budget_amount=budget_decimal,
            status="pendiente",
        )
        db.session.add(folio)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("No se pudo crear el folio. Revisa que no este duplicado.", "error")
        return _render_folios_page(status_code=400, form_data=form_data)

    log_action(
        user_id=session.get("user_id"),
        action="folio_created",
        entity="folio",
        entity_id=folio.id,
        details=f"singa={folio.singa_number}",
    )
    workflow = ensure_workflow(folio)
    db.session.add(workflow)
    for deliverable in ensure_deliverables(folio):
        db.session.add(deliverable)
    db.session.commit()

    flash("Folio creado correctamente.", "success")
    return redirect(url_for("folios.list_folios"))


@folios_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@roles_required("ui", "direccion")
def create_folio():
    if request.method == "POST":
        return list_folios()
    return redirect(url_for("folios.list_folios", tab="alta"))


@folios_bp.route("/<int:folio_id>/estado", methods=["POST"])
@login_required
def update_folio_status(folio_id):
    if session.get("role") not in ALLOWED_STATUS_UPDATE_ROLES:
        flash("No tienes permisos para actualizar estatus.", "error")
        return redirect(url_for("folios.list_folios"))

    folio = Folio.query.get_or_404(folio_id)
    new_status = request.form.get("status", "").strip()
    if new_status not in ALLOWED_FOLIO_STATUSES:
        flash("Estatus invalido.", "error")
        return redirect(url_for("folios.list_folios"))

    old_status = folio.status
    folio.status = new_status
    db.session.add(folio)
    db.session.commit()

    log_action(
        user_id=session.get("user_id"),
        action="folio_status_updated",
        entity="folio",
        entity_id=folio.id,
        details=f"from={old_status};to={new_status}",
    )
    flash("Estatus de folio actualizado.", "success")
    next_url = request.form.get("next", "").strip()
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("folios.list_folios"))
