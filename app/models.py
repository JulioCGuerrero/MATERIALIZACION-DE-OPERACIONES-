"""Modelos de base de datos (SQLAlchemy).

Cada clase representa una tabla y sus relaciones/reglas.
"""

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Role(db.Model):
    """Tabla `Role` en la base de datos."""
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class User(db.Model):
    """Tabla `User` en la base de datos."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    role = db.relationship("Role", lazy="joined")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Provider(db.Model):
    """Tabla `Provider` en la base de datos."""
    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    provider_type = db.Column(db.String(20), nullable=False)
    sat_status = db.Column(db.String(20), nullable=False, default="pendiente")
    sat_valid_until = db.Column(db.Date, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "provider_type IN ('outsourcing', 'materiales', 'servicios')",
            name="ck_provider_type",
        ),
    )


class AuthorizedAccount(db.Model):
    """Tabla `AuthorizedAccount` en la base de datos."""
    __tablename__ = "authorized_accounts"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False)
    bank = db.Column(db.String(80), nullable=False)
    clabe = db.Column(db.String(18), unique=True, nullable=False)
    rfc = db.Column(db.String(13), nullable=False)
    authorized_by = db.Column(db.String(120), nullable=False)
    authorized_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    provider = db.relationship("Provider", lazy="joined")

    __table_args__ = (db.CheckConstraint("length(clabe) = 18", name="ck_clabe_length"),)


class Folio(db.Model):
    """Tabla `Folio` en la base de datos."""
    __tablename__ = "folios"

    id = db.Column(db.Integer, primary_key=True)
    singa_number = db.Column(db.String(30), unique=True, nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False)
    provider_type = db.Column(db.String(20), nullable=False)
    communication_responsible = db.Column(db.String(120), nullable=False)
    contract_amount = db.Column(db.Numeric(12, 2), nullable=False)
    budget_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pendiente")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    provider = db.relationship("Provider", lazy="joined")

    __table_args__ = (
        db.CheckConstraint(
            "provider_type IN ('outsourcing', 'materiales', 'servicios')",
            name="ck_folio_provider_type",
        ),
        db.CheckConstraint(
            "status IN ('pendiente', 'en_proceso', 'listo_para_cierre', 'cerrado', 'alerta', 'critico')",
            name="ck_folio_status",
        ),
        db.CheckConstraint("budget_amount > 0", name="ck_folio_budget_positive"),
    )


class Deliverable(db.Model):
    """Tabla `Deliverable` en la base de datos."""
    __tablename__ = "deliverables"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    owner_area = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente")

    folio = db.relationship("Folio", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("status IN ('pendiente', 'subido', 'validado')", name="ck_deliverable_status"),
    )


class Transfer(db.Model):
    """Tabla `Transfer` en la base de datos."""
    __tablename__ = "transfers"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("authorized_accounts.id"), nullable=False)
    spei_reference = db.Column(db.String(80), nullable=False)
    origin_bank = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transfer_date = db.Column(db.Date, nullable=False)
    approved_by_direction = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    folio = db.relationship("Folio", lazy="joined")
    account = db.relationship("AuthorizedAccount", lazy="joined")


class AuditLog(db.Model):
    """Tabla `AuditLog` en la base de datos."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    entity = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", lazy="joined")


class ProviderCompliance(db.Model):
    """Tabla `ProviderCompliance` en la base de datos."""
    __tablename__ = "provider_compliance"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False, unique=True)
    sat_opinion_status = db.Column(db.String(20), nullable=False, default="no_cargada")
    sat_valid_until = db.Column(db.Date, nullable=True)
    efos_flag = db.Column(db.Boolean, nullable=False, default=False)
    activity_match = db.Column(db.Boolean, nullable=False, default=False)
    rfc_matches_account = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    provider = db.relationship("Provider", lazy="joined")

    __table_args__ = (
        db.CheckConstraint(
            "sat_opinion_status IN ('no_cargada', 'vigente', 'vencida')",
            name="ck_sat_opinion_status",
        ),
    )


class FolioWorkflow(db.Model):
    """Tabla `FolioWorkflow` en la base de datos."""
    __tablename__ = "folio_workflow"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False, unique=True)
    step_1_ui_folio = db.Column(db.Boolean, nullable=False, default=True)
    step_2_contab_sat = db.Column(db.Boolean, nullable=False, default=False)
    step_3_ui_deliverables = db.Column(db.Boolean, nullable=False, default=False)
    step_4_tesoreria_transfer = db.Column(db.Boolean, nullable=False, default=False)
    step_5_contab_cfdi = db.Column(db.Boolean, nullable=False, default=False)
    step_6_contab_reconciliation = db.Column(db.Boolean, nullable=False, default=False)
    step_7_ui_ready_to_close = db.Column(db.Boolean, nullable=False, default=False)
    step_8_contab_closed = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    folio = db.relationship("Folio", lazy="joined")


class FolioDeliverableItem(db.Model):
    """Tabla `FolioDeliverableItem` en la base de datos."""
    __tablename__ = "folio_deliverable_items"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    code = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    owner_area = db.Column(db.String(20), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    uploaded = db.Column(db.Boolean, nullable=False, default=False)
    uploaded_at = db.Column(db.DateTime, nullable=True)

    folio = db.relationship("Folio", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("owner_area IN ('ui', 'contabilidad')", name="ck_deliverable_owner_area"),
    )


class CfdiRecord(db.Model):
    """Tabla `CfdiRecord` en la base de datos."""
    __tablename__ = "cfdi_records"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    uuid = db.Column(db.String(64), nullable=False, unique=True)
    xml_ref = db.Column(db.String(255), nullable=False)
    pdf_ref = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    issued_at = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="vigente")
    cancel_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    folio = db.relationship("Folio", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("status IN ('vigente', 'cancelado')", name="ck_cfdi_status"),
    )


class BudgetConfig(db.Model):
    """Tabla `BudgetConfig` en la base de datos."""
    __tablename__ = "budget_config"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    period = db.Column(db.String(7), nullable=False)
    authorized_budget = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    folio = db.relationship("Folio", lazy="joined")


class BankMovement(db.Model):
    """Tabla `BankMovement` en la base de datos."""
    __tablename__ = "bank_movements"

    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.String(7), nullable=False)
    bank = db.Column(db.String(50), nullable=False)
    movement_date = db.Column(db.Date, nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)
    reference = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=True)
    is_reconciled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    folio = db.relationship("Folio", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("movement_type IN ('deposito', 'retiro')", name="ck_movement_type"),
    )


class ReconciliationAlert(db.Model):
    """Tabla `ReconciliationAlert` en la base de datos."""
    __tablename__ = "reconciliation_alerts"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("bank_movements.id"), nullable=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="media")
    status = db.Column(db.String(20), nullable=False, default="abierta")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    folio = db.relationship("Folio", lazy="joined")
    movement = db.relationship("BankMovement", lazy="joined")

    __table_args__ = (
        db.CheckConstraint(
            "alert_type IN ('deposito_sin_folio', 'excede_presupuesto', 'cuenta_no_autorizada', 'diferencia_cfdi_banco')",
            name="ck_alert_type",
        ),
        db.CheckConstraint("severity IN ('media', 'alta')", name="ck_alert_severity"),
        db.CheckConstraint("status IN ('abierta', 'resuelta')", name="ck_alert_status"),
    )


class MonthlyDirectionReport(db.Model):
    """Tabla `MonthlyDirectionReport` en la base de datos."""
    __tablename__ = "monthly_direction_reports"

    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.String(7), nullable=False, unique=True)
    executive_summary = db.Column(db.Text, nullable=False)
    risk_summary = db.Column(db.Text, nullable=False)
    recommendations = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    creator = db.relationship("User", lazy="joined")


class EvidenceFile(db.Model):
    """Tabla `EvidenceFile` en la base de datos."""
    __tablename__ = "evidence_files"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=True)
    deliverable_id = db.Column(db.Integer, db.ForeignKey("folio_deliverable_items.id"), nullable=True)
    category = db.Column(db.String(30), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    folio = db.relationship("Folio", lazy="joined")
    deliverable = db.relationship("FolioDeliverableItem", lazy="joined")
    uploader = db.relationship("User", lazy="joined")

    __table_args__ = (
        db.CheckConstraint(
            "category IN ('entregable', 'cfdi_xml', 'cfdi_pdf', 'sat_opinion', 'bank_statement', 'otro')",
            name="ck_evidence_category",
        ),
    )


class SignatureAck(db.Model):
    """Tabla `SignatureAck` en la base de datos."""
    __tablename__ = "signature_acks"

    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(20), nullable=False, unique=True)
    signer_name = db.Column(db.String(120), nullable=False)
    signed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.CheckConstraint("area IN ('ui', 'contabilidad')", name="ck_ack_area"),
    )

