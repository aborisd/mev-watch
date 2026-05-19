-- MEV-Watch schema. Addresses are 20-byte BYTEA, tx/block hashes 32-byte BYTEA.
-- Wei amounts are NUMERIC(78,0) to fit uint256 losslessly.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ───────────────────────────── blocks ─────────────────────────────
CREATE TABLE IF NOT EXISTS blocks (
    number          BIGINT PRIMARY KEY,
    hash            BYTEA NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    base_fee        NUMERIC(78, 0),
    builder         BYTEA,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- NULL = not yet scanned by detector
    detected_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_blocks_ts ON blocks(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_blocks_undetected ON blocks(number) WHERE detected_at IS NULL;

-- ────────────────────────── transactions ──────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    hash                BYTEA PRIMARY KEY,
    block_number        BIGINT NOT NULL REFERENCES blocks(number) ON DELETE CASCADE,
    tx_index            INT NOT NULL,
    from_address        BYTEA NOT NULL,
    to_address          BYTEA,
    gas_used            BIGINT,
    gas_price           NUMERIC(78, 0),
    max_priority_fee    NUMERIC(78, 0),
    value               NUMERIC(78, 0),
    success             BOOLEAN NOT NULL,
    -- Sum of direct ETH transfers from this tx to the block builder (coinbase)
    bribe_to_builder    NUMERIC(78, 0) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tx_block ON transactions(block_number, tx_index);
CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_address);

-- ──────────────────────────── tokens ──────────────────────────────
CREATE TABLE IF NOT EXISTS tokens (
    address     BYTEA PRIMARY KEY,
    symbol      TEXT,
    decimals    INT,
    name        TEXT
);

-- ────────────────────────────── pools ─────────────────────────────
CREATE TABLE IF NOT EXISTS pools (
    address     BYTEA PRIMARY KEY,
    protocol    TEXT NOT NULL,    -- 'uni_v2' | 'uni_v3'
    token0      BYTEA NOT NULL,
    token1      BYTEA NOT NULL,
    fee_tier    INT               -- V3 only (500, 3000, 10000)
);
CREATE INDEX IF NOT EXISTS idx_pools_tokens ON pools(token0, token1);

-- ────────────────────────────── swaps ─────────────────────────────
CREATE TABLE IF NOT EXISTS swaps (
    tx_hash         BYTEA NOT NULL,
    log_index       INT NOT NULL,
    block_number    BIGINT NOT NULL,
    block_ts        TIMESTAMPTZ NOT NULL,
    tx_index        INT NOT NULL,
    pool            BYTEA NOT NULL,
    protocol        TEXT NOT NULL,
    sender          BYTEA NOT NULL,
    recipient       BYTEA NOT NULL,
    token_in        BYTEA NOT NULL,
    token_out       BYTEA NOT NULL,
    amount_in       NUMERIC(78, 0) NOT NULL,
    amount_out      NUMERIC(78, 0) NOT NULL,
    PRIMARY KEY (tx_hash, log_index, block_ts)
);
-- Hypertable on block_ts for fast range queries.
SELECT create_hypertable('swaps', 'block_ts', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_swaps_pool_block ON swaps(pool, block_number);
CREATE INDEX IF NOT EXISTS idx_swaps_sender ON swaps(sender);
CREATE INDEX IF NOT EXISTS idx_swaps_block ON swaps(block_number);

-- ───────────────────── V3 liquidity events (Mint/Burn) ────────────
CREATE TABLE IF NOT EXISTS v3_liquidity_events (
    tx_hash         BYTEA NOT NULL,
    log_index       INT NOT NULL,
    block_number    BIGINT NOT NULL,
    block_ts        TIMESTAMPTZ NOT NULL,
    tx_index        INT NOT NULL,
    pool            BYTEA NOT NULL,
    event_type      TEXT NOT NULL,    -- 'mint' | 'burn'
    owner           BYTEA NOT NULL,
    tick_lower      INT NOT NULL,
    tick_upper      INT NOT NULL,
    liquidity       NUMERIC(78, 0) NOT NULL,
    amount0         NUMERIC(78, 0),
    amount1         NUMERIC(78, 0),
    PRIMARY KEY (tx_hash, log_index, block_ts)
);
SELECT create_hypertable('v3_liquidity_events', 'block_ts', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_v3liq_pool_block ON v3_liquidity_events(pool, block_number);
CREATE INDEX IF NOT EXISTS idx_v3liq_block ON v3_liquidity_events(block_number);

-- ─────────────────────── detected MEV events ──────────────────────
CREATE TABLE IF NOT EXISTS mev_events (
    id                  BIGSERIAL,
    block_number        BIGINT NOT NULL,
    block_ts            TIMESTAMPTZ NOT NULL,
    event_type          TEXT NOT NULL,    -- 'sandwich' | 'jit'
    extractor_eoa       BYTEA NOT NULL,
    extractor_contract  BYTEA,
    victim_eoa          BYTEA,
    pool                BYTEA NOT NULL,

    gross_profit_wei    NUMERIC(78, 0),
    gross_profit_token  BYTEA,
    gas_cost_wei        NUMERIC(78, 0),
    bribe_wei           NUMERIC(78, 0) NOT NULL DEFAULT 0,
    net_profit_wei      NUMERIC(78, 0),
    net_profit_usd      NUMERIC(18, 2),

    frontrun_tx         BYTEA,
    victim_tx           BYTEA,
    backrun_tx          BYTEA,

    metadata            JSONB,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, block_ts)
);
SELECT create_hypertable('mev_events', 'block_ts', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_mev_extractor ON mev_events(extractor_eoa);
CREATE INDEX IF NOT EXISTS idx_mev_type_ts ON mev_events(event_type, block_ts DESC);
CREATE INDEX IF NOT EXISTS idx_mev_profit ON mev_events(net_profit_usd DESC) WHERE net_profit_usd IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mev_block ON mev_events(block_number);

-- Dedup: same sandwich shouldn't be inserted twice if detector re-runs.
-- Hypertable unique indexes MUST include the partitioning column (block_ts).
-- COALESCE expressions need parens.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_mev_event
    ON mev_events(
        event_type,
        block_number,
        block_ts,
        extractor_eoa,
        pool,
        (COALESCE(frontrun_tx, ''::bytea)),
        (COALESCE(victim_tx, ''::bytea))
    );

-- ─────────────────────── ETH/USD price snapshots ──────────────────
CREATE TABLE IF NOT EXISTS eth_usd_prices (
    block_number    BIGINT PRIMARY KEY,
    price_usd       NUMERIC(18, 6) NOT NULL
);

-- ─────────────────────── NOTIFY channel for SSE ───────────────────
-- API listens on channel 'mev_events_new' for live streaming.
CREATE OR REPLACE FUNCTION notify_mev_event() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('mev_events_new', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_mev_event ON mev_events;
CREATE TRIGGER trg_notify_mev_event
AFTER INSERT ON mev_events
FOR EACH ROW EXECUTE FUNCTION notify_mev_event();
