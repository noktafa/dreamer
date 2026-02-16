CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    correlation_id  UUID NOT NULL,
    customer_id     VARCHAR(50) NOT NULL,
    amount          DECIMAL(15,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'TRY',
    status          VARCHAR(20) NOT NULL DEFAULT 'PROCESSED',
    source_server   VARCHAR(100),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_correlation_id ON orders(correlation_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);

CREATE TABLE IF NOT EXISTS dead_letters (
    id              SERIAL PRIMARY KEY,
    correlation_id  UUID,
    payload         JSONB,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
