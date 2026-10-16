PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_sk INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL,
    segment TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_business_key
    ON dim_customer(customer_id);

CREATE INDEX IF NOT EXISTS idx_dim_customer_current
    ON dim_customer(customer_id, is_current);

CREATE UNIQUE INDEX IF NOT EXISTS uq_one_current_version
    ON dim_customer(customer_id)
    WHERE is_current = 1;

CREATE TABLE IF NOT EXISTS processed_batches (
    batch_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_count INTEGER NOT NULL,
    inserted_versions INTEGER NOT NULL,
    skipped_rows INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS change_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    changed_fields_json TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES processed_batches(batch_id)
);
