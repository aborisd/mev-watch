"""Ethereum RPC clients (HTTP + WebSocket) + global rate limiter."""

from __future__ import annotations

import asyncio
import random
from typing import Any, Awaitable, Callable, TypeVar

from web3 import AsyncWeb3
from web3.providers.persistent import WebSocketProvider
from web3.providers.rpc import AsyncHTTPProvider

from .config import settings


def make_http_w3() -> AsyncWeb3:
    """Long-lived HTTP client for eth_call, eth_getBlockByNumber, eth_getLogs."""
    return AsyncWeb3(AsyncHTTPProvider(settings.eth_http_url))


def make_ws_provider() -> WebSocketProvider:
    """WS provider; wrap with `async with AsyncWeb3(provider) as w3:` to connect."""
    return WebSocketProvider(settings.eth_ws_url)


async def rpc_call(w3: AsyncWeb3, method: str, params: list[Any] | None = None) -> Any:
    """Fallback raw JSON-RPC when web3.py has no typed helper."""
    return await w3.manager.coro_request(method, params or [])


# ─── Global throttle ──────────────────────────────────────────────
# Bounds concurrent RPC requests across the whole process. Free-tier providers
# (Chainstack, Alchemy) respond with HTTP 429 when hit in parallel; 4 keeps us
# well under typical 25 RPS limits while preserving useful parallelism.
_RPC_SEMAPHORE = asyncio.Semaphore(4)

T = TypeVar("T")


async def with_retry(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    retries: int = 5,
    base_delay: float = 0.5,
) -> T:
    """Run `coro_factory()` through the semaphore with exponential backoff on 429."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        async with _RPC_SEMAPHORE:
            try:
                return await coro_factory()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                msg = str(e)
                transient = "429" in msg or "Too Many Requests" in msg or "rate limit" in msg.lower()
                if attempt == retries - 1 or not transient:
                    raise
        await asyncio.sleep(base_delay * (2 ** attempt) + random.random() * 0.25)
    assert last_exc is not None
    raise last_exc
