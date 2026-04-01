from decimal import Decimal

from flask import flash, redirect, render_template, request, session, url_for

from app.audit import log_action
from app.auth.routes import login_required, roles_required
from app.extensions import db
from app.folios import folios_bp
from app.models import AuthorizedAccount, Folio, Provider


@folios_bp.route("/")
@login_required
def list_folios():
    items = Folio.query.order_by(Folio.created_at.desc()).all()
    return render_template("folios/list.html", folios=items)


@folios_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@roles_required("ui", "direccion")
def create_folio():
    providers = Provider.query.order_by(Provider.name.asc()).all()

    if request.method == "POST":
        singa_number = request.form.get("singa_number", "").strip()
        provider_id = request.form.get("provider_id")
        responsible = request.form.get("communication_responsible", "").strip()
        budget_amount = request.form.get("budget_amount", "0").strip()
        contract_amount = request.form.get("contract_amount", "0").strip()

        if not singa_number:
            flash("El número de folio SINGA es obligatorio.", "error")
            return render_template("folios/create.html", providers=providers), 400

        provider = Provider.query.get(int(provider_id)) if provider_id else None
        if not provider:
            flash("Proveedor inválido.", "error")
            return render_template("folios/create.html", providers=providers), 400

        has_authorized_account = (
            AuthorizedAccount.query.filter_by(provider_id=provider.id, is_active=True).count() > 0
        )

        if not has_authorized_account:
            flash(
                "Bloqueo duro: no se puede crear un folio con proveedor sin cuenta autorizada.",
                "error",
            )
            log_action(
                user_id=session.get("user_id"),
                action="folio_creation_blocked",
                entity="folio",
                details=f"provider={provider.name};reason=no_authorized_account",
            )
            return render_template("folios/create.html", providers=providers), 400

        try:
            folio = Folio(
                singa_number=singa_number,
                provider_id=provider.id,
                provider_type=provider.provider_type,
                communication_responsible=responsible,
                contract_amount=Decimal(contract_amount),
                budget_amount=Decimal(budget_amount),
                status="pendiente",
            )
            db.session.add(folio)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("No se pudo crear el folio. Revisa que no esté duplicado.", "error")
            return render_template("folios/create.html", providers=providers), 400

        log_action(
            user_id=session.get("user_id"),
            action="folio_created",
            entity="folio",
            entity_id=folio.id,
            details=f"singa={folio.singa_number}",
        )
        flash("Folio creado correctamente.", "success")
        return redirect(url_for("folios.list_folios"))

    return render_template("folios/create.html", providers=providers)
