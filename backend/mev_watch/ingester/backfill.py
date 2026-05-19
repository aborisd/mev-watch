"""One-shot historical catch-up: enqueue the most recent N blocks prior to current MIN(blocks)."""

from __future__ import annotations

import asyncio

from web3 import AsyncWeb3

from ..config import settings
from ..logging import get_logger
from .listener import SeenSet

log = get_logger(__name__)


async def run_backfill(
    w3: AsyncWeb3,
    db_pool,
    queue: asyncio.Queue,
    seen: SeenSet,
) -> None:
    depth = settings.backfill_blocks
    if depth <= 0:
        log.info("backfill_disabled")
        return

    async with db_pool.acquire() as conn:
        min_block = await conn.fetchval("SELECT MIN(number) FROM blocks")

    if min_block is None:
        try:
            min_block = await w3.eth.block_number
        except Exception as e:  # noqa: BLE001
            log.error("backfill_head_fetch_failed", err=str(e))
            return

    from_block = min_block - 1
    to_block = max(0, from_block - depth + 1)
    if from_block < to_block:
        return
    log.info("backfill_start", from_block=from_block, to_block=to_block, depth=depth)

    # Walk newest → oldest so recent history appears first.
    for n in range(from_block, to_block - 1, -1):
        if seen.add(n):
            await queue.put(n)
            # Queue is bounded; this naturally backpressures.
    log.info("backfill_enqueued", count=from_block - to_block + 1)
