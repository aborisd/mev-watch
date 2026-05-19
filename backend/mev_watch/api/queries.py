"""SQL kept in one place, parameterised by asyncpg $N."""

EVENT_COLS = """
    id, event_type, block_number, block_ts,
    extractor_eoa, extractor_contract, victim_eoa, pool,
    gross_profit_wei, gross_profit_token, gas_cost_wei,
    net_profit_wei, net_profit_usd,
    frontrun_tx, victim_tx, backrun_tx
"""

EVENT_DETAIL_COLS = EVENT_COLS + ", metadata, detected_at"


SQL_LIST_EVENTS_BASE = f"""
SELECT {EVENT_COLS}
FROM mev_events
WHERE 1 = 1
"""


SQL_EVENT_DETAIL = f"""
SELECT {EVENT_DETAIL_COLS}
FROM mev_events
WHERE id = $1
LIMIT 1
"""


from datetime import timedelta


def period_to_interval(period: str) -> timedelta:
    mapping = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    return mapping.get(period, timedelta(hours=24))


def bucket_for_period(period: str) -> timedelta:
    mapping = {
        "1h": timedelta(minutes=5),
        "24h": timedelta(hours=1),
        "7d": timedelta(hours=6),
        "30d": timedelta(days=1),
    }
    return mapping.get(period, timedelta(hours=1))


SQL_LEADERBOARD = """
SELECT
    extractor_eoa AS address,
    COUNT(*) AS attack_count,
    COALESCE(SUM(net_profit_usd), 0) AS total_profit_usd,
    AVG(net_profit_usd) AS avg_profit_usd
FROM mev_events
WHERE block_ts >= NOW() - $1::interval
  AND ($2::text IS NULL OR event_type = $2)
GROUP BY extractor_eoa
ORDER BY
    CASE WHEN $3 = 'count' THEN COUNT(*) END DESC NULLS LAST,
    COALESCE(SUM(net_profit_usd), 0) DESC
LIMIT 50
"""


SQL_STATS = """
SELECT
    COUNT(*) AS attack_count,
    COALESCE(SUM(net_profit_usd), 0) AS total_profit_usd,
    COUNT(DISTINCT victim_eoa) AS unique_victims,
    AVG(net_profit_usd) AS avg_profit_usd
FROM mev_events
WHERE block_ts >= NOW() - $1::interval
"""


SQL_TOP_POOLS = """
SELECT
    pool,
    COUNT(*) AS attack_count,
    COALESCE(SUM(net_profit_usd), 0) AS total_profit_usd
FROM mev_events
WHERE block_ts >= NOW() - $1::interval
GROUP BY pool
ORDER BY total_profit_usd DESC NULLS LAST
LIMIT 10
"""


SQL_TIMESERIES = """
SELECT
    time_bucket($2::interval, block_ts) AS bucket,
    COALESCE(SUM(net_profit_usd), 0) AS profit_usd,
    COUNT(*) AS count
FROM mev_events
WHERE block_ts >= NOW() - $1::interval
GROUP BY bucket
ORDER BY bucket ASC
"""


SQL_ADDRESS_EVENTS = f"""
SELECT {EVENT_COLS}
FROM mev_events
WHERE extractor_eoa = $1
ORDER BY block_ts DESC
LIMIT $2
"""


SQL_ADDRESS_STATS = """
SELECT
    COUNT(*) AS attack_count,
    COALESCE(SUM(net_profit_usd), 0) AS total_profit_usd
FROM mev_events
WHERE extractor_eoa = $1
"""


SQL_ADDRESS_POOLS = """
SELECT pool,
       COUNT(*) AS attack_count,
       COALESCE(SUM(net_profit_usd), 0) AS total_profit_usd
FROM mev_events
WHERE extractor_eoa = $1
GROUP BY pool
ORDER BY total_profit_usd DESC NULLS LAST
LIMIT 10
"""
