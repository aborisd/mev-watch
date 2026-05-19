"""Detector loop — polls for undetected blocks and runs sandwich/JIT detectors."""

from __future__ import annotations

import asyncio
import signal

from ..config import settings
from ..db import close_pool, init_pool
from ..logging import configure_logging, get_logger
from .runner import detect_block, fetch_pending_blocks

log = get_logger(__name__)


async def main() -> None:
    configure_logging()
    log.info("detector_start",
             interval_sec=settings.detector_interval_sec,
             min_profit_usd=settings.min_net_profit_usd)
    db_pool = await init_pool(min_size=2, max_size=8)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, stop.set)
        except NotImplementedError:
            pass

    try:
        while not stop.is_set():
            try:
                pending = await fetch_pending_blocks(db_pool, limit=200)
                if not pending:
                    await _sleep_or_stop(stop, settings.detector_interval_sec)
                    continue
                total_sw = total_jit = 0
                for b in pending:
                    sw, jit = await detect_block(db_pool, b)
                    total_sw += sw
                    total_jit += jit
                log.info("detector_pass_done",
                         blocks=len(pending), sandwich=total_sw, jit=total_jit)
            except Exception as e:  # noqa: BLE001
                log.error("detector_loop_error", err=str(e))
                await _sleep_or_stop(stop, settings.detector_interval_sec)
    finally:
        await close_pool()
        log.info("detector_stopped")


async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
