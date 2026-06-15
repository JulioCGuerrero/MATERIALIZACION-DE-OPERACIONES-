from datetime import date, datetime

from .extensions import db


class Proveedor(db.Model):
    __tablename__ = "proveedores"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    rfc = db.Column(db.String, nullable=False, unique=True)
    tipo = db.Column(db.String, nullable=False)
    nivel = db.Column(db.Integer, nullable=False)
    banco = db.Column(db.String)
    cuenta = db.Column(db.String)
    clabe = db.Column(db.String)
    repse = db.Column(db.Boolean, default=False)
    tiene_fisico = db.Column(db.Boolean, default=False)
    efos_ok = db.Column(db.Boolean, default=True)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    folios = db.relationship("Folio", back_populates="proveedor", cascade="all, delete-orphan")


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False, unique=True)
    nombre = db.Column(db.String, nullable=False)
    rol = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False, unique=True)
    rfc = db.Column(db.String, nullable=False, unique=True)
    tipo_empresa = db.Column(db.String, nullable=False, default="servicios")
    activo = db.Column(db.Boolean, default=True)
    onboarding_status = db.Column(db.String, nullable=False, default="borrador")
    onboarding_aprobada_en = db.Column(db.DateTime)
    onboarding_aprobada_por = db.Column(db.String)
    reglas_negocio = db.Column(db.JSON, nullable=False, default=dict)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    folios = db.relationship("Folio", back_populates="empresa", cascade="all, delete-orphan")
    documentos = db.relationship("EmpresaDocumento", back_populates="empresa", cascade="all, delete-orphan")
    cuentas_bancarias = db.relationship("EmpresaCuentaBancaria", back_populates="empresa", cascade="all, delete-orphan")


class EmpresaDocumento(db.Model):
    __tablename__ = "empresa_documentos"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    nombre_archivo = db.Column(db.String)
    url = db.Column(db.String)
    estado_validacion = db.Column(db.String, nullable=False, default="pendiente")
    observaciones = db.Column(db.Text)
    vigente_hasta = db.Column(db.Date)
    subido_por = db.Column(db.String)
    validado_por = db.Column(db.String)
    subido_en = db.Column(db.DateTime, default=datetime.utcnow)
    validado_en = db.Column(db.DateTime)

    empresa = db.relationship("Empresa", back_populates="documentos")


class EmpresaCuentaBancaria(db.Model):
    __tablename__ = "empresa_cuentas_bancarias"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    banco = db.Column(db.String, nullable=False)
    titular = db.Column(db.String, nullable=False)
    clabe = db.Column(db.String, nullable=False)
    numero_cuenta = db.Column(db.String)
    moneda = db.Column(db.String, default="MXN")
    activa = db.Column(db.Boolean, default=True)
    validada = db.Column(db.Boolean, default=False)
    validada_por = db.Column(db.String)
    validada_en = db.Column(db.DateTime)
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizada_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = db.relationship("Empresa", back_populates="cuentas_bancarias")


class Folio(db.Model):
    __tablename__ = "folios"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String, nullable=False, unique=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=True)
    presupuesto = db.Column(db.Float, nullable=False)
    periodo = db.Column(db.String, nullable=False)
    fecha_limite_entrega = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String, default="activo")
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    cerrado_en = db.Column(db.DateTime)

    proveedor = db.relationship("Proveedor", back_populates="folios")
    empresa = db.relationship("Empresa", back_populates="folios")
    expediente = db.relationship("Expediente", back_populates="folio", uselist=False, cascade="all, delete-orphan")
    traspasos = db.relationship("Traspaso", back_populates="folio", cascade="all, delete-orphan")


class Expediente(db.Model):
    __tablename__ = "expedientes"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    completitud = db.Column(db.Float, default=0.0)
    pago_bloqueado = db.Column(db.Boolean, default=True)
    razon_negocio = db.Column(db.Text)
    manifiesto = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    folio = db.relationship("Folio", back_populates="expediente")
    documentos = db.relationship("Documento", back_populates="expediente", cascade="all, delete-orphan")


class Documento(db.Model):
    __tablename__ = "documentos"

    id = db.Column(db.Integer, primary_key=True)
    expediente_id = db.Column(db.Integer, db.ForeignKey("expedientes.id"), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    nombre_archivo = db.Column(db.String)
    url = db.Column(db.String)
    subido = db.Column(db.Boolean, default=False)
    subido_en = db.Column(db.DateTime)
    subido_por = db.Column(db.String)
    validacion_estado = db.Column(db.String, default="pendiente")
    validacion_detalle = db.Column(db.Text)
    validado_en = db.Column(db.DateTime)
    validado_por = db.Column(db.String)

    expediente = db.relationship("Expediente", back_populates="documentos")


class Traspaso(db.Model):
    __tablename__ = "traspasos"

    id = db.Column(db.Integer, primary_key=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=False)
    folio_bancario = db.Column(db.String)
    banco_origen = db.Column(db.String, nullable=False)
    banco_destino = db.Column(db.String)
    cuenta_destino = db.Column(db.String)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.String, nullable=False)
    estado = db.Column(db.String, default="pendiente")
    excede_presup = db.Column(db.Boolean, default=False)
    diferencia = db.Column(db.Float, default=0.0)
    registrado_por = db.Column(db.String)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    folio = db.relationship("Folio", back_populates="traspasos")


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    tabla = db.Column(db.String, nullable=False)
    tabla_id = db.Column(db.Integer, nullable=False)
    accion = db.Column(db.String, nullable=False)
    detalle = db.Column(db.Text)
    usuario = db.Column(db.String)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class EfosRegistro(db.Model):
    __tablename__ = "efos_registro"

    id = db.Column(db.Integer, primary_key=True)
    rfc = db.Column(db.String, nullable=False, unique=True)
    publicado_en_sat = db.Column(db.Boolean, default=True)
    fuente = db.Column(db.String, default="sat")
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alerta(db.Model):
    __tablename__ = "alertas"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String, nullable=False)
    severidad = db.Column(db.String, nullable=False, default="amarillo")
    mensaje = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String, nullable=False, default="activa")
    origen = db.Column(db.String, nullable=False, default="auto")
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=True)
    folio_id = db.Column(db.Integer, db.ForeignKey("folios.id"), nullable=True)
    expediente_id = db.Column(db.Integer, db.ForeignKey("expedientes.id"), nullable=True)
    periodo = db.Column(db.String, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proveedor = db.relationship("Proveedor")
    empresa = db.relationship("Empresa")
    folio = db.relationship("Folio")
    expediente = db.relationship("Expediente")


class PolicySet(db.Model):
    __tablename__ = "policy_sets"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, unique=True)
    nombre = db.Column(db.String, nullable=False, default="Politica Operativa")
    activa_version_id = db.Column(db.Integer, db.ForeignKey("policy_versions.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = db.relationship("Empresa")
    versiones = db.relationship(
        "PolicyVersion",
        back_populates="policy_set",
        cascade="all, delete-orphan",
        foreign_keys="PolicyVersion.policy_set_id",
    )


class PolicyVersion(db.Model):
    __tablename__ = "policy_versions"

    id = db.Column(db.Integer, primary_key=True)
    policy_set_id = db.Column(db.Integer, db.ForeignKey("policy_sets.id"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String, nullable=False, default="draft")
    parametros = db.Column(db.JSON, nullable=False, default=dict)
    creado_por = db.Column(db.String)
    nota_cambio = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    publicado_en = db.Column(db.DateTime)

    policy_set = db.relationship("PolicySet", back_populates="versiones", foreign_keys=[policy_set_id])

    __table_args__ = (
        db.UniqueConstraint("policy_set_id", "version", name="uq_policy_version"),
    )


class PolicyEvaluation(db.Model):
    __tablename__ = "policy_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    policy_version_id = db.Column(db.Integer, db.ForeignKey("policy_versions.id"), nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=True)
    expediente_id = db.Column(db.Integer, db.ForeignKey("expedientes.id"), nullable=True)
    tipo = db.Column(db.String, nullable=False, default="clasificacion")
    input_payload = db.Column(db.JSON, nullable=False, default=dict)
    output_payload = db.Column(db.JSON, nullable=False, default=dict)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    policy_version = db.relationship("PolicyVersion")
    empresa = db.relationship("Empresa")
    proveedor = db.relationship("Proveedor")
    expediente = db.relationship("Expediente")


class EmpresaCredencial(db.Model):
    __tablename__ = "empresa_credenciales"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, unique=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    empresa = db.relationship("Empresa")


class ProveedorCredencial(db.Model):
    __tablename__ = "proveedor_credenciales"

    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    proveedor = db.relationship("Proveedor")
    empresa = db.relationship("Empresa")

    __table_args__ = (
        db.UniqueConstraint("proveedor_id", "empresa_id", name="uq_proveedor_empresa_credencial"),
    )
