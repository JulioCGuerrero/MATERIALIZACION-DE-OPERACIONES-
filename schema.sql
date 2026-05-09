CREATE TABLE proveedores (
	id INTEGER NOT NULL, 
	nombre VARCHAR NOT NULL, 
	rfc VARCHAR NOT NULL, 
	tipo VARCHAR NOT NULL, 
	nivel INTEGER NOT NULL, 
	banco VARCHAR, 
	cuenta VARCHAR, 
	clabe VARCHAR, 
	repse BOOLEAN, 
	tiene_fisico BOOLEAN, 
	efos_ok BOOLEAN, 
	activo BOOLEAN, 
	creado_en DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (rfc)
);
CREATE TABLE usuarios (
	id INTEGER NOT NULL, 
	email VARCHAR NOT NULL, 
	nombre VARCHAR NOT NULL, 
	rol VARCHAR NOT NULL, 
	password VARCHAR NOT NULL, 
	activo BOOLEAN, 
	creado_en DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);
CREATE TABLE empresas (
	id INTEGER NOT NULL, 
	nombre VARCHAR NOT NULL, 
	rfc VARCHAR NOT NULL, 
	tipo_empresa VARCHAR NOT NULL, 
	activo BOOLEAN, 
	creado_en DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (nombre), 
	UNIQUE (rfc)
);
CREATE TABLE audit_log (
	id INTEGER NOT NULL, 
	tabla VARCHAR NOT NULL, 
	tabla_id INTEGER NOT NULL, 
	accion VARCHAR NOT NULL, 
	detalle TEXT, 
	usuario VARCHAR, 
	creado_en DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE efos_registro (
	id INTEGER NOT NULL, 
	rfc VARCHAR NOT NULL, 
	publicado_en_sat BOOLEAN, 
	fuente VARCHAR, 
	actualizado_en DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (rfc)
);
CREATE TABLE folios (
	id INTEGER NOT NULL, 
	numero VARCHAR NOT NULL, 
	proveedor_id INTEGER NOT NULL, 
	empresa_id INTEGER, 
	presupuesto FLOAT NOT NULL, 
	periodo VARCHAR NOT NULL, 
	fecha_limite_entrega DATE, 
	estado VARCHAR, 
	creado_en DATETIME, 
	cerrado_en DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (numero), 
	FOREIGN KEY(proveedor_id) REFERENCES proveedores (id), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id)
);
CREATE TABLE expedientes (
	id INTEGER NOT NULL, 
	folio_id INTEGER NOT NULL, 
	completitud FLOAT, 
	pago_bloqueado BOOLEAN, 
	razon_negocio TEXT, 
	manifiesto BOOLEAN, 
	creado_en DATETIME, 
	actualizado_en DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(folio_id) REFERENCES folios (id)
);
CREATE TABLE traspasos (
	id INTEGER NOT NULL, 
	folio_id INTEGER NOT NULL, 
	folio_bancario VARCHAR, 
	banco_origen VARCHAR NOT NULL, 
	banco_destino VARCHAR, 
	cuenta_destino VARCHAR, 
	monto FLOAT NOT NULL, 
	fecha VARCHAR NOT NULL, 
	estado VARCHAR, 
	excede_presup BOOLEAN, 
	diferencia FLOAT, 
	registrado_por VARCHAR, 
	creado_en DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(folio_id) REFERENCES folios (id)
);
CREATE TABLE documentos (
	id INTEGER NOT NULL, 
	expediente_id INTEGER NOT NULL, 
	tipo VARCHAR NOT NULL, 
	nombre_archivo VARCHAR, 
	url VARCHAR, 
	subido BOOLEAN, 
	subido_en DATETIME, 
	subido_por VARCHAR, 
	validacion_estado VARCHAR, 
	validacion_detalle TEXT, 
	validado_en DATETIME, 
	validado_por VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(expediente_id) REFERENCES expedientes (id)
);
CREATE TABLE alertas (
	id INTEGER NOT NULL, 
	tipo VARCHAR NOT NULL, 
	severidad VARCHAR NOT NULL, 
	mensaje TEXT NOT NULL, 
	estado VARCHAR NOT NULL, 
	origen VARCHAR NOT NULL, 
	proveedor_id INTEGER, 
	empresa_id INTEGER, 
	folio_id INTEGER, 
	expediente_id INTEGER, 
	periodo VARCHAR, 
	creado_en DATETIME, 
	actualizado_en DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(proveedor_id) REFERENCES proveedores (id), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id), 
	FOREIGN KEY(folio_id) REFERENCES folios (id), 
	FOREIGN KEY(expediente_id) REFERENCES expedientes (id)
);
