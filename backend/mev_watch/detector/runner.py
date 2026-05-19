"""Load block-level data, run detectors, persist MEV events."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from ..config import settings
from ..logging import get_logger
from .economics import Economics, jit_economics, sandwich_economics
from .jit import detect_jits
from .sandwich import detect_sandwiches
from .types import DetectLiq, DetectSwap, JITCandidate, SandwichCandidate

log = get_logger(__name__)


# ─── SQL ──────────────────────────────────────────────────────────

_SQL_LOAD_SWAPS = """
SELECT s.tx_hash, s.log_index, s.tx_index, s.block_number, s.block_ts,
       s.pool, s.protocol, s.sender, s.recipient,
       s.token_in, s.token_out, s.amount_in, s.amount_out,
       t.to_address AS tx_to, t.gas_used, t.gas_price
FROM swaps s
JOIN transactions t ON t.hash = s.tx_hash
WHERE s.block_number = $1
ORDER BY s.tx_index, s.log_index
"""

_SQL_LOAD_LIQ = """
SELECT l.tx_hash, l.log_index, l.tx_index, l.block_number, l.block_ts,
       l.pool, l.event_type, l.owner,
       l.tick_lower, l.tick_upper, l.liquidity, l.amount0, l.amount1,
       t.from_address AS sender, t.to_address AS tx_to,
       t.gas_used, t.gas_price
FROM v3_liquidity_events l
JOIN transactions t ON t.hash = l.tx_hash
WHERE l.block_number = $1
ORDER BY l.tx_index, l.log_index
"""

_SQL_POOL_INFO = "SELECT token0, token1, fee_tier FROM pools WHERE address = $1"

_SQL_INSERT_EVENT = """
INSERT INTO mev_events
    (block_number, block_ts, event_type,
     extractor_eoa, extractor_contract, victim_eoa, pool,
     gross_profit_wei, gross_profit_token, gas_cost_wei,
     bribe_wei, net_profit_wei, net_profit_usd,
     frontrun_tx, victim_tx, backrun_tx, metadata)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17::jsonb)
ON CONFLICT DO NOTHING
"""


# ─── Row → dataclass ──────────────────────────────────────────────

def _row_to_swap(row: dict[str, Any]) -> DetectSwap:
    return DetectSwap(
        tx_hash=bytes(row["tx_hash"]),
        log_index=row["log_index"],
        tx_index=row["tx_index"],
        block_number=row["block_number"],
        block_ts=row["block_ts"],
        pool=bytes(row["pool"]),
        protocol=row["protocol"],
        sender=bytes(row["sender"]),
        tx_to=bytes(row["tx_to"]) if row["tx_to"] is not None else None,
        recipient=bytes(row["recipient"]),
        token_in=bytes(row["token_in"]),
        token_out=bytes(row["token_out"]),
        amount_in=int(row["amount_in"]),
        amount_out=int(row["amount_out"]),
        gas_used=int(row["gas_used"] or 0),
        gas_price=int(row["gas_price"] or 0),
    )


def _row_to_liq(row: dict[str, Any]) -> DetectLiq:
    return DetectLiq(
        tx_hash=bytes(row["tx_hash"]),
        log_index=row["log_index"],
        tx_index=row["tx_index"],
        block_number=row["block_number"],
        block_ts=row["block_ts"],
        pool=bytes(row["pool"]),
        event_type=row["event_type"],
        owner=bytes(row["owner"]),
        tick_lower=row["tick_lower"],
        tick_upper=row["tick_upper"],
        liquidity=int(row["liquidity"]),
        amount0=int(row["amount0"] or 0),
        amount1=int(row["amount1"] or 0),
        sender=bytes(row["sender"]),
        tx_to=bytes(row["tx_to"]) if row["tx_to"] is not None else None,
        gas_used=int(row["gas_used"] or 0),
        gas_price=int(row["gas_price"] or 0),
    )


# ─── Runner ───────────────────────────────────────────────────────

async def _load_block(db_pool, block_number: int) -> tuple[list[DetectSwap], list[DetectLiq]]:
    async with db_pool.acquire() as conn:
        swap_rows = await conn.fetch(_SQL_LOAD_SWAPS, block_number)
        liq_rows = await conn.fetch(_SQL_LOAD_LIQ, block_number)
    swaps = [_row_to_swap(dict(r)) for r in swap_rows]
    liqs = [_row_to_liq(dict(r)) for r in liq_rows]
    return swaps, liqs


async def _insert_sandwich(db_pool, sc: SandwichCandidate, econ: Economics) -> bool:
    if econ.net_profit_usd is not None and econ.net_profit_usd < Decimal(str(settings.min_net_profit_usd)):
        return False
    metadata = {
        "front_tx_index": sc.front.tx_index,
        "victim_tx_index": sc.victim.tx_index,
        "back_tx_index": sc.back.tx_index,
        "quote_unavailable": econ.quote_unavailable,
    }
    # Same-contract → treat it as the extractor's contract.
    extractor_contract = None
    if sc.front.tx_to is not None and sc.front.tx_to == sc.back.tx_to:
        extractor_contract = sc.front.tx_to

    async with db_pool.acquire() as conn:
        res = await conn.execute(
            _SQL_INSERT_EVENT,
            sc.front.block_number, sc.front.block_ts, "sandwich",
            sc.front.sender, extractor_contract, sc.victim.sender, sc.pool,
            Decimal(econ.gross_profit_wei) if econ.gross_profit_wei is not None else None,
            econ.gross_profit_token,
            Decimal(econ.gas_cost_wei),
            Decimal(0),
            Decimal(econ.net_profit_wei) if econ.net_profit_wei is not None else None,
            econ.net_profit_usd,
            sc.front.tx_hash, sc.victim.tx_hash, sc.back.tx_hash,
            json.dumps(metadata),
        )
    return "INSERT" in res and res.split()[-1] != "0"


async def _insert_jit(db_pool, jc: JITCandidate, econ: Economics) -> bool:
    if econ.net_profit_usd is not None and econ.net_profit_usd < Decimal(str(settings.min_net_profit_usd)):
        return False
    metadata = {
        "mint_tx_index": jc.mint.tx_index,
        "victim_tx_index": jc.victim.tx_index,
        "burn_tx_index": jc.burn.tx_index,
        "tick_lower": jc.mint.tick_lower,
        "tick_upper": jc.mint.tick_upper,
        "liquidity": str(jc.mint.liquidity),
        "quote_unavailable": econ.quote_unavailable,
    }
    extractor_contract = None
    if jc.mint.tx_to is not None and jc.mint.tx_to == jc.burn.tx_to:
        extractor_contract = jc.mint.tx_to

    async with db_pool.acquire() as conn:
        res = await conn.execute(
            _SQL_INSERT_EVENT,
            jc.mint.block_number, jc.mint.block_ts, "jit",
            jc.mint.sender, extractor_contract, jc.victim.sender, jc.pool,
            Decimal(econ.gross_profit_wei) if econ.gross_profit_wei is not None else None,
            econ.gross_profit_token,
            Decimal(econ.gas_cost_wei),
            Decimal(0),
            Decimal(econ.net_profit_wei) if econ.net_profit_wei is not None else None,
            econ.net_profit_usd,
            jc.mint.tx_hash, jc.victim.tx_hash, jc.burn.tx_hash,
            json.dumps(metadata),
        )
    return "INSERT" in res and res.split()[-1] != "0"


async def detect_block(db_pool, block_number: int) -> tuple[int, int]:
    """Run detectors on one block. Returns (sandwich_count, jit_count) persisted."""
    swaps, liqs = await _load_block(db_pool, block_number)

    sw_found = 0
    jit_found = 0

    if swaps:
        sandwiches = detect_sandwiches(swaps)
        for sc in sandwiches:
            front_gas = sc.front.gas_used * sc.front.gas_price
            back_gas = sc.back.gas_used * sc.back.gas_price
            # Gross profit: back.amount_out − front.amount_in, in front.token_in
            gross_token = sc.front.token_in
            gross_amount = sc.back.amount_out - sc.front.amount_in
            econ = await sandwich_economics(
                db_pool, front_gas, back_gas, gross_token, gross_amount, block_number,
            )
            if await _insert_sandwich(db_pool, sc, econ):
                sw_found += 1

    if liqs:
        jits = detect_jits(swaps, liqs)
        for jc in jits:
            mint_gas = jc.mint.gas_used * jc.mint.gas_price
            burn_gas = jc.burn.gas_used * jc.burn.gas_price
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(_SQL_POOL_INFO, jc.pool)
            if row is None:
                continue
            fee_tier = row["fee_tier"]
            econ = await jit_economics(
                db_pool,
                jc.victim.token_in, jc.victim.amount_in, fee_tier,
                mint_gas, burn_gas, block_number,
            )
            if await _insert_jit(db_pool, jc, econ):
                jit_found += 1

    # Mark block as scanned even if nothing found.
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE blocks SET detected_at = NOW() WHERE number = $1",
            block_number,
        )

    if sw_found or jit_found:
        log.info("detect_block", block=block_number, sandwich=sw_found, jit=jit_found)
    return sw_found, jit_found


async def fetch_pending_blocks(db_pool, limit: int = 100) -> list[int]:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT number FROM blocks
            WHERE detected_at IS NULL
            ORDER BY number ASC
            LIMIT $1
            """,
            limit,
        )
    return [r["number"] for r in rows]
