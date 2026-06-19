DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_policy_sets_activa_version'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'policy_sets_activa_version_id_fkey'
    ) THEN
        ALTER TABLE materializacion_operaciones.policy_sets
            RENAME CONSTRAINT fk_policy_sets_activa_version
            TO policy_sets_activa_version_id_fkey;
    END IF;
END $$;
