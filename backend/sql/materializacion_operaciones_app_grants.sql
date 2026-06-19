GRANT USAGE ON SCHEMA materializacion_operaciones TO materializacion_app;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA materializacion_operaciones
TO materializacion_app;

GRANT USAGE, SELECT, UPDATE
ON ALL SEQUENCES IN SCHEMA materializacion_operaciones
TO materializacion_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA materializacion_operaciones
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO materializacion_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA materializacion_operaciones
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO materializacion_app;
