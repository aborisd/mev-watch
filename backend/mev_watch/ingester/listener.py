"""WebSocket subscription to new block heads. Enqueues block numbers for workers."""

from __future__ import annotations

import asyncio
from collections import deque

from web3 import AsyncWeb3

from ..config import settings
from ..logging import get_logger
from ..rpc import make_ws_provider

log = get_logger(__name__)


class SeenSet:
    """Bounded FIFO set for deduplicating recently-enqueued block numbers."""

    def __init__(self, max_size: int = 512):
        self._items: set[int] = set()
        self._order: deque[int] = deque()
        self._max = max_size

    def add(self, n: int) -> bool:
        if n in self._items:
            return False
        self._items.add(n)
        self._order.append(n)
        if len(self._order) > self._max:
            old = self._order.popleft()
            self._items.discard(old)
        return True


async def run_listener(queue: asyncio.Queue, seen: SeenSet) -> None:
    """Connect to WS, subscribe to newHeads, enqueue (N − BLOCK_CONFIRMATIONS)."""
    backoff = 1.0
    confirmations = settings.block_confirmations
    while True:
        try:
            provider = make_ws_provider()
            async with AsyncWeb3(provider) as w3:
                log.info("ws_connected")
                await w3.eth.subscribe("newHeads")
                backoff = 1.0
                async for msg in w3.socket.process_subscriptions():
                    # `msg` shape: {'subscription': id, 'result': {...header...}}
                    result = msg.get("result") if isinstance(msg, dict) else None
                    if result is None:
                        continue
                    num_raw = result.get("number")
                    if num_raw is None:
                        continue
                    head = int(num_raw, 16) if isinstance(num_raw, str) else int(num_raw)
                    target = head - confirmations
                    if target < 0:
                        continue
                    if seen.add(target):
                        await queue.put(target)
                        log.debug("enqueue_head", head=head, target=target)
        except Exception as e:  # noqa: BLE001
            log.warning("ws_disconnected", err=str(e), retry_in=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
