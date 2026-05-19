"""Process a single block: fetch data, decode logs, persist."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from web3 import AsyncWeb3

from ..constants import PROTO_V2, PROTO_V3
from ..logging import get_logger
from ..rpc import with_retry
from ..utils import hexint, to_bytes
from .decoding import LiquidityLog, SwapLog, decode_log
from .prices import fetch_eth_usd_price, write_eth_usd_price
from .reference import ReferenceCache

log = get_logger(__name__)


def _as_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 16) if v.startswith(("0x", "0X")) else int(v)
    raise TypeError(f"cannot int-ify {type(v)}")


def _as_bytes(v: Any) -> bytes | None:
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray, memoryview)):
        return bytes(v)
    return to_bytes(v)


async def process_block(
    w3: AsyncWeb3,
    db_pool,
    ref: ReferenceCache,
    block_number: int,
) -> None:
    """Fetch block + receipts, decode relevant logs, persist in one DB transaction."""
    try:
        block = await with_retry(
            lambda: w3.eth.get_block(block_number, full_transactions=True)
        )
        receipts = await with_retry(
            lambda: w3.eth.get_block_receipts(block_number)
        )
    except Exception as e:  # noqa: BLE001
        log.warning("block_fetch_failed", block=block_number, err=str(e))
        return

    block_hash = _as_bytes(block["hash"])
    timestamp = datetime.fromtimestamp(_as_int(block["timestamp"]), tz=timezone.utc)
    base_fee_raw = block.get("baseFeePerGas")
    base_fee = Decimal(_as_int(base_fee_raw)) if base_fee_raw is not None else None
    builder = _as_bytes(block.get("miner"))

    # Index full transactions by hash for quick lookup when walking receipts.
    txs_by_hash: dict[bytes, Any] = {}
    for tx in block["transactions"]:
        h = _as_bytes(tx["hash"])
        if h is not None:
            txs_by_hash[h] = tx

    # First pass: decode only receipts that carry at least one relevant log.
    relevant: list[tuple[Any, Any, list[SwapLog | LiquidityLog], int]] = []
    for r in receipts:
        tx_hash_b = _as_bytes(r["transactionHash"])
        if tx_hash_b is None:
            continue
        tx = txs_by_hash.get(tx_hash_b)
        if tx is None:
            continue
        tx_index = _as_int(r["transactionIndex"])
        decoded: list[SwapLog | LiquidityLog] = []
        for L in r.get("logs") or []:
            try:
                d = decode_log(L, tx_index)
            except Exception as e:  # noqa: BLE001
                log.debug("log_decode_failed", block=block_number, err=str(e))
                continue
            if d is not None:
                decoded.append(d)
        if decoded:
            relevant.append((tx, r, decoded, tx_index))

    # Bootstrap all referenced pools concurrently (idempotent, cached).
    uniq_pools: dict[bytes, str] = {}
    for _tx, _r, decoded, _ti in relevant:
        for d in decoded:
            if isinstance(d, SwapLog):
                uniq_pools[d.pool] = d.protocol
            else:
                uniq_pools.setdefault(d.pool, PROTO_V3)
    if uniq_pools:
        await asyncio.gather(
            *[ref.ensure_pool(p, proto) for p, proto in uniq_pools.items()],
            return_exceptions=True,
        )

    # Build row lists.
    tx_rows: list[tuple] = []
    swap_rows: list[tuple] = []
    liq_rows: list[tuple] = []

    for tx, r, decoded, tx_index in relevant:
        from_addr = _as_bytes(tx["from"])
        to_addr = _as_bytes(tx.get("to"))
        gas_used = _as_int(r["gasUsed"])
        # Prefer receipt.effectiveGasPrice (canonical for EIP-1559); fall back to tx.gasPrice.
        egp = r.get("effectiveGasPrice")
        if egp is not None:
            gas_price = Decimal(_as_int(egp))
        elif tx.get("gasPrice") is not None:
            gas_price = Decimal(_as_int(tx["gasPrice"]))
        else:
            gas_price = None
        mpf = tx.get("maxPriorityFeePerGas")
        max_priority = Decimal(_as_int(mpf)) if mpf is not None else None
        value = Decimal(_as_int(tx.get("value", 0) or 0))
        status = _as_int(r.get("status", 0)) == 1
        tx_hash_b = _as_bytes(r["transactionHash"])

        tx_rows.append((
            tx_hash_b, block_number, tx_index,
            from_addr, to_addr,
            gas_used, gas_price, max_priority, value,
            status,
        ))

        for d in decoded:
            if isinstance(d, SwapLog):
                proto = d.protocol
                pi = await ref.ensure_pool(d.pool, proto)
                if pi is None:
                    continue
                if proto == PROTO_V2:
                    if d.amount0_in > 0 and d.amount1_out > 0:
                        t_in, t_out = pi.token0, pi.token1
                        a_in, a_out = d.amount0_in, d.amount1_out
                    elif d.amount1_in > 0 and d.amount0_out > 0:
                        t_in, t_out = pi.token1, pi.token0
                        a_in, a_out = d.amount1_in, d.amount0_out
                    else:
                        continue  # malformed V2 swap
                else:  # PROTO_V3
                    if d.amount0 > 0 and d.amount1 < 0:
                        t_in, t_out = pi.token0, pi.token1
                        a_in, a_out = d.amount0, -d.amount1
                    elif d.amount1 > 0 and d.amount0 < 0:
                        t_in, t_out = pi.token1, pi.token0
                        a_in, a_out = d.amount1, -d.amount0
                    else:
                        continue

                swap_rows.append((
                    d.tx_hash, d.log_index, block_number, timestamp, tx_index,
                    d.pool, proto,
                    from_addr,       # sender = EOA that signed the tx
                    d.recipient,     # recipient of token_out (from event)
                    t_in, t_out,
                    Decimal(a_in), Decimal(a_out),
                ))
            else:
                liq_rows.append((
                    d.tx_hash, d.log_index, block_number, timestamp, tx_index,
                    d.pool, d.event_type, d.owner,
                    d.tick_lower, d.tick_upper,
                    Decimal(d.liquidity),
                    Decimal(d.amount0) if d.amount0 is not None else None,
                    Decimal(d.amount1) if d.amount1 is not None else None,
                ))

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO blocks (number, hash, timestamp, base_fee, builder)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (number) DO UPDATE SET
                    hash = EXCLUDED.hash,
                    timestamp = EXCLUDED.timestamp,
                    base_fee = EXCLUDED.base_fee,
                    builder = EXCLUDED.builder,
                    detected_at = NULL
                """,
                block_number, block_hash, timestamp, base_fee, builder,
            )
            if tx_rows:
                await conn.executemany(
                    """
                    INSERT INTO transactions
                        (hash, block_number, tx_index, from_address, to_address,
                         gas_used, gas_price, max_priority_fee, value, success)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT (hash) DO NOTHING
                    """,
                    tx_rows,
                )
            if swap_rows:
                await conn.executemany(
                    """
                    INSERT INTO swaps
                        (tx_hash, log_index, block_number, block_ts, tx_index,
                         pool, protocol, sender, recipient, token_in, token_out,
                         amount_in, amount_out)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    ON CONFLICT DO NOTHING
                    """,
                    swap_rows,
                )
            if liq_rows:
                await conn.executemany(
                    """
                    INSERT INTO v3_liquidity_events
                        (tx_hash, log_index, block_number, block_ts, tx_index,
                         pool, event_type, owner, tick_lower, tick_upper,
                         liquidity, amount0, amount1)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    ON CONFLICT DO NOTHING
                    """,
                    liq_rows,
                )

    # Price snapshot (non-critical — failure doesn't block ingest).
    price = await fetch_eth_usd_price(w3, block_number)
    if price is not None:
        try:
            await write_eth_usd_price(db_pool, block_number, price)
        except Exception as e:  # noqa: BLE001
            log.debug("price_write_failed", block=block_number, err=str(e))

    log.info(
        "block_processed",
        number=block_number, swaps=len(swap_rows), liq=len(liq_rows), txs=len(tx_rows),
    )


async def run_worker(
    w3: AsyncWeb3,
    db_pool,
    ref: ReferenceCache,
    queue: asyncio.Queue,
    worker_id: int,
) -> None:
    """Consume block numbers from the queue and process them."""
    log.info("worker_start", id=worker_id)
    while True:
        block_number = await queue.get()
        try:
            await process_block(w3, db_pool, ref, block_number)
        except Exception as e:  # noqa: BLE001
            log.error("worker_exception", id=worker_id, block=block_number, err=str(e))
        finally:
            queue.task_done()
