from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class User(db.Model):
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
    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    provider_type = db.Column(
        db.String(20),
        nullable=False,
    )
    sat_status = db.Column(db.String(20), nullable=False, default="pendiente")
    sat_valid_until = db.Column(db.Date, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "provider_type IN ('outsourcing', 'materiales', 'servicios')",
            name="ck_provider_type",
        ),
    )


class AuthorizedAccount(db.Model):
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

    __table_args__ = (
        db.CheckConstraint("length(clabe) = 18", name="ck_clabe_length"),
    )


class Folio(db.Model):
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
    __tablename__ = "deliverables"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    owner_area = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente")

    folio = db.relationship("Folio", lazy="joined")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pendiente', 'subido', 'validado')",
            name="ck_deliverable_status",
        ),
    )


class Transfer(db.Model):
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
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    entity = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", lazy="joined")
