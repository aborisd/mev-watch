"""Ingester entry point. Runs listener + N workers + optional backfill."""

from __future__ import annotations

import asyncio
import signal

from ..config import settings
from ..db import close_pool, init_pool
from ..logging import configure_logging, get_logger
from ..rpc import make_http_w3
from .backfill import run_backfill
from .listener import SeenSet, run_listener
from .reference import ReferenceCache
from .worker import run_worker

log = get_logger(__name__)


async def main() -> None:
    configure_logging()
    log.info("ingester_start", workers=settings.ingester_workers,
             confirmations=settings.block_confirmations,
             backfill=settings.backfill_blocks)

    db_pool = await init_pool(min_size=2, max_size=max(settings.ingester_workers * 2, 4))
    w3 = make_http_w3()
    ref = ReferenceCache(w3, db_pool)

    queue: asyncio.Queue[int] = asyncio.Queue(maxsize=256)
    seen = SeenSet(max_size=2048)

    tasks: list[asyncio.Task] = []
    for i in range(settings.ingester_workers):
        tasks.append(asyncio.create_task(run_worker(w3, db_pool, ref, queue, i), name=f"worker-{i}"))
    tasks.append(asyncio.create_task(run_listener(queue, seen), name="listener"))
    tasks.append(asyncio.create_task(run_backfill(w3, db_pool, queue, seen), name="backfill"))

    stop_event = asyncio.Event()

    def _on_signal():
        log.info("shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _on_signal)
        except NotImplementedError:
            pass

    await stop_event.wait()
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass
        except Exception as e:  # noqa: BLE001
            log.warning("task_exit_error", task=t.get_name(), err=str(e))
    await close_pool()
    log.info("ingester_stopped")


if __name__ == "__main__":
    asyncio.run(main())
