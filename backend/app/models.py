from datetime import datetime

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


class Folio(db.Model):
    __tablename__ = "folios"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String, nullable=False, unique=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=False)
    presupuesto = db.Column(db.Float, nullable=False)
    periodo = db.Column(db.String, nullable=False)
    estado = db.Column(db.String, default="activo")
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    cerrado_en = db.Column(db.DateTime)

    proveedor = db.relationship("Proveedor", back_populates="folios")
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
