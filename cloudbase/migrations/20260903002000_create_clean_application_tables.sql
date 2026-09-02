CREATE TABLE IF NOT EXISTS clean.task_reports (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    original_name TEXT NOT NULL,
    entrust_date VARCHAR(32),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    input_rows INTEGER NOT NULL DEFAULT 0,
    output_rows INTEGER NOT NULL DEFAULT 0,
    blocking_count INTEGER NOT NULL DEFAULT 0,
    audit_count INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    source_object_key TEXT,
    output_file TEXT,
    output_url TEXT,
    output_object_key TEXT,
    report_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_task_reports_task_id UNIQUE (task_id)
);

CREATE TABLE IF NOT EXISTS clean.app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clean.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    must_change_password BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_username UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS clean.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_sessions_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_user_sessions_user_id_users
        FOREIGN KEY (user_id) REFERENCES clean.users (id) ON DELETE CASCADE
);

ALTER TABLE clean.task_reports
    ADD COLUMN IF NOT EXISTS user_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_task_reports_user_id_users'
          AND conrelid = 'clean.task_reports'::regclass
    ) THEN
        ALTER TABLE clean.task_reports
            ADD CONSTRAINT fk_task_reports_user_id_users
            FOREIGN KEY (user_id) REFERENCES clean.users (id) ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id
    ON clean.user_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at
    ON clean.user_sessions (expires_at);
CREATE INDEX IF NOT EXISTS ix_task_reports_user_id
    ON clean.task_reports (user_id);

CREATE TABLE IF NOT EXISTS clean.alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);

INSERT INTO clean.alembic_version (version_num)
VALUES ('0002_users_and_report_ownership')
ON CONFLICT (version_num) DO NOTHING;

GRANT USAGE ON SCHEMA clean TO clean_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA clean TO clean_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA clean TO clean_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA clean
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO clean_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA clean
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO clean_app;
