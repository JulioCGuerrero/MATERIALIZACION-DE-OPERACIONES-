-- MATERIALIZACION OPERACIONES
-- Esquema base para PostgreSQL
-- Ejecutar en una base vacia o con IF NOT EXISTS habilitado.

BEGIN;

CREATE TABLE IF NOT EXISTS proveedores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    rfc VARCHAR NOT NULL UNIQUE,
    tipo VARCHAR NOT NULL,
    nivel INTEGER NOT NULL,
    banco VARCHAR,
    cuenta VARCHAR,
    clabe VARCHAR,
    repse BOOLEAN DEFAULT FALSE,
    tiene_fisico BOOLEAN DEFAULT FALSE,
    efos_ok BOOLEAN DEFAULT TRUE,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    nombre VARCHAR NOT NULL,
    rol VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL UNIQUE,
    rfc VARCHAR NOT NULL UNIQUE,
    tipo_empresa VARCHAR NOT NULL DEFAULT 'servicios',
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS folios (
    id SERIAL PRIMARY KEY,
    numero VARCHAR NOT NULL UNIQUE,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    empresa_id INTEGER REFERENCES empresas(id),
    presupuesto DOUBLE PRECISION NOT NULL,
    periodo VARCHAR NOT NULL,
    fecha_limite_entrega DATE,
    estado VARCHAR DEFAULT 'activo',
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cerrado_en TIMESTAMP WITHOUT TIME ZONE
);

CREATE TABLE IF NOT EXISTS expedientes (
    id SERIAL PRIMARY KEY,
    folio_id INTEGER NOT NULL REFERENCES folios(id),
    completitud DOUBLE PRECISION DEFAULT 0.0,
    pago_bloqueado BOOLEAN DEFAULT TRUE,
    razon_negocio TEXT,
    manifiesto BOOLEAN DEFAULT FALSE,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documentos (
    id SERIAL PRIMARY KEY,
    expediente_id INTEGER NOT NULL REFERENCES expedientes(id),
    tipo VARCHAR NOT NULL,
    nombre_archivo VARCHAR,
    url VARCHAR,
    subido BOOLEAN DEFAULT FALSE,
    subido_en TIMESTAMP WITHOUT TIME ZONE,
    subido_por VARCHAR,
    validacion_estado VARCHAR DEFAULT 'pendiente',
    validacion_detalle TEXT,
    validado_en TIMESTAMP WITHOUT TIME ZONE,
    validado_por VARCHAR
);

CREATE TABLE IF NOT EXISTS traspasos (
    id SERIAL PRIMARY KEY,
    folio_id INTEGER NOT NULL REFERENCES folios(id),
    folio_bancario VARCHAR,
    banco_origen VARCHAR NOT NULL,
    banco_destino VARCHAR,
    cuenta_destino VARCHAR,
    monto DOUBLE PRECISION NOT NULL,
    fecha VARCHAR NOT NULL,
    estado VARCHAR DEFAULT 'pendiente',
    excede_presup BOOLEAN DEFAULT FALSE,
    diferencia DOUBLE PRECISION DEFAULT 0.0,
    registrado_por VARCHAR,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    tabla VARCHAR NOT NULL,
    tabla_id INTEGER NOT NULL,
    accion VARCHAR NOT NULL,
    detalle TEXT,
    usuario VARCHAR,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS efos_registro (
    id SERIAL PRIMARY KEY,
    rfc VARCHAR NOT NULL UNIQUE,
    publicado_en_sat BOOLEAN DEFAULT TRUE,
    fuente VARCHAR DEFAULT 'sat',
    actualizado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alertas (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR NOT NULL,
    severidad VARCHAR NOT NULL DEFAULT 'amarillo',
    mensaje TEXT NOT NULL,
    estado VARCHAR NOT NULL DEFAULT 'activa',
    origen VARCHAR NOT NULL DEFAULT 'auto',
    proveedor_id INTEGER REFERENCES proveedores(id),
    empresa_id INTEGER REFERENCES empresas(id),
    folio_id INTEGER REFERENCES folios(id),
    expediente_id INTEGER REFERENCES expedientes(id),
    periodo VARCHAR,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS policy_sets (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL UNIQUE REFERENCES empresas(id),
    nombre VARCHAR NOT NULL DEFAULT 'Politica Operativa',
    activa_version_id INTEGER,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS policy_versions (
    id SERIAL PRIMARY KEY,
    policy_set_id INTEGER NOT NULL REFERENCES policy_sets(id),
    version INTEGER NOT NULL,
    estado VARCHAR NOT NULL DEFAULT 'draft',
    parametros JSONB NOT NULL DEFAULT '{}'::jsonb,
    creado_por VARCHAR,
    nota_cambio TEXT,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    publicado_en TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_policy_version UNIQUE (policy_set_id, version)
);

ALTER TABLE policy_sets
    DROP CONSTRAINT IF EXISTS policy_sets_activa_version_id_fkey;
ALTER TABLE policy_sets
    ADD CONSTRAINT policy_sets_activa_version_id_fkey
    FOREIGN KEY (activa_version_id) REFERENCES policy_versions(id);

CREATE TABLE IF NOT EXISTS policy_evaluations (
    id SERIAL PRIMARY KEY,
    policy_version_id INTEGER REFERENCES policy_versions(id),
    empresa_id INTEGER REFERENCES empresas(id),
    proveedor_id INTEGER REFERENCES proveedores(id),
    expediente_id INTEGER REFERENCES expedientes(id),
    tipo VARCHAR NOT NULL DEFAULT 'clasificacion',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proveedor_credenciales (
    id SERIAL PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_proveedor_empresa_credencial UNIQUE (proveedor_id, empresa_id)
);

-- Indices recomendados para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_folios_empresa_id ON folios(empresa_id);
CREATE INDEX IF NOT EXISTS idx_folios_proveedor_id ON folios(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_expedientes_folio_id ON expedientes(folio_id);
CREATE INDEX IF NOT EXISTS idx_documentos_expediente_id ON documentos(expediente_id);
CREATE INDEX IF NOT EXISTS idx_traspasos_folio_id ON traspasos(folio_id);
CREATE INDEX IF NOT EXISTS idx_alertas_estado ON alertas(estado);
CREATE INDEX IF NOT EXISTS idx_alertas_periodo ON alertas(periodo);
CREATE INDEX IF NOT EXISTS idx_audit_log_creado_en ON audit_log(creado_en);

COMMIT;
