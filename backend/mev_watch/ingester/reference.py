"""Lazy bootstrap of pools and tokens on first encounter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from web3 import AsyncWeb3
from web3.exceptions import ContractLogicError

from ..abi import ERC20_ABI, V2_PAIR_ABI, V3_POOL_ABI
from ..constants import PROTO_V2, PROTO_V3
from ..logging import get_logger
from ..rpc import with_retry
from ..utils import addr, to_bytes

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PoolInfo:
    address: bytes
    protocol: str
    token0: bytes
    token1: bytes
    fee_tier: int | None


class ReferenceCache:
    """In-memory LRU for pools/tokens. Persists new entries to DB on first sight."""

    def __init__(self, w3: AsyncWeb3, db_pool, max_pools: int = 50_000, max_tokens: int = 50_000):
        self.w3 = w3
        self.db = db_pool
        self._pools: dict[bytes, PoolInfo] = {}
        self._tokens: set[bytes] = set()
        self._pool_locks: dict[bytes, asyncio.Lock] = {}
        self._token_locks: dict[bytes, asyncio.Lock] = {}
        self._max_pools = max_pools
        self._max_tokens = max_tokens

    def _lock(self, addr_b: bytes, store: dict) -> asyncio.Lock:
        lk = store.get(addr_b)
        if lk is None:
            lk = asyncio.Lock()
            store[addr_b] = lk
        return lk

    async def ensure_pool(self, pool_addr: bytes, protocol: str) -> PoolInfo | None:
        cached = self._pools.get(pool_addr)
        if cached is not None:
            return cached
        async with self._lock(pool_addr, self._pool_locks):
            cached = self._pools.get(pool_addr)
            if cached is not None:
                return cached
            # DB first
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT address, protocol, token0, token1, fee_tier FROM pools WHERE address = $1",
                    pool_addr,
                )
            if row:
                pi = PoolInfo(
                    address=bytes(row["address"]),
                    protocol=row["protocol"],
                    token0=bytes(row["token0"]),
                    token1=bytes(row["token1"]),
                    fee_tier=row["fee_tier"],
                )
                self._cache_pool(pi)
                return pi
            # RPC bootstrap
            pi = await self._bootstrap_pool(pool_addr, protocol)
            if pi is None:
                return None
            async with self.db.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO pools (address, protocol, token0, token1, fee_tier)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (address) DO NOTHING
                    """,
                    pi.address, pi.protocol, pi.token0, pi.token1, pi.fee_tier,
                )
            self._cache_pool(pi)
            # Kick off token bootstrap (fire-and-forget; not critical for ingest correctness)
            asyncio.create_task(self.ensure_token(pi.token0))
            asyncio.create_task(self.ensure_token(pi.token1))
            return pi

    async def _bootstrap_pool(self, pool_addr: bytes, protocol: str) -> PoolInfo | None:
        checksum = self.w3.to_checksum_address(addr(pool_addr))
        try:
            if protocol == PROTO_V3:
                c = self.w3.eth.contract(address=checksum, abi=V3_POOL_ABI)
                # Serialise the three calls through the semaphore instead of firing in parallel.
                token0 = await with_retry(lambda: c.functions.token0().call())
                token1 = await with_retry(lambda: c.functions.token1().call())
                try:
                    fee_tier = await with_retry(lambda: c.functions.fee().call())
                except (ContractLogicError, Exception):  # noqa: BLE001
                    fee_tier = None
                return PoolInfo(
                    address=pool_addr,
                    protocol=PROTO_V3,
                    token0=to_bytes(token0),
                    token1=to_bytes(token1),
                    fee_tier=int(fee_tier) if fee_tier is not None else None,
                )
            # V2
            c = self.w3.eth.contract(address=checksum, abi=V2_PAIR_ABI)
            token0 = await with_retry(lambda: c.functions.token0().call())
            token1 = await with_retry(lambda: c.functions.token1().call())
            return PoolInfo(
                address=pool_addr,
                protocol=PROTO_V2,
                token0=to_bytes(token0),
                token1=to_bytes(token1),
                fee_tier=None,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("pool_bootstrap_failed", pool=addr(pool_addr), proto=protocol, err=str(e))
            return None

    def _cache_pool(self, pi: PoolInfo) -> None:
        if len(self._pools) >= self._max_pools:
            # Drop a random entry (simple LRU substitute).
            self._pools.pop(next(iter(self._pools)))
        self._pools[pi.address] = pi

    async def ensure_token(self, token_addr: bytes) -> None:
        if token_addr in self._tokens:
            return
        async with self._lock(token_addr, self._token_locks):
            if token_addr in self._tokens:
                return
            async with self.db.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT 1 FROM tokens WHERE address = $1", token_addr
                )
            if exists:
                self._tokens.add(token_addr)
                return
            symbol, decimals, name = await self._bootstrap_token(token_addr)
            async with self.db.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO tokens (address, symbol, decimals, name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (address) DO NOTHING
                    """,
                    token_addr, symbol, decimals, name,
                )
            self._tokens.add(token_addr)
            if len(self._tokens) > self._max_tokens:
                self._tokens.pop()

    async def _bootstrap_token(self, token_addr: bytes) -> tuple[str | None, int | None, str | None]:
        checksum = self.w3.to_checksum_address(addr(token_addr))
        c = self.w3.eth.contract(address=checksum, abi=ERC20_ABI)

        async def _safe(coro):
            try:
                return await coro
            except Exception:  # noqa: BLE001
                return None

        symbol = await _safe(with_retry(lambda: c.functions.symbol().call()))
        decimals = await _safe(with_retry(lambda: c.functions.decimals().call()))
        name = await _safe(with_retry(lambda: c.functions.name().call()))
        # Some tokens return bytes32 for symbol/name; handle that.
        if isinstance(symbol, (bytes, bytearray)):
            symbol = symbol.rstrip(b"\x00").decode("utf-8", errors="replace")
        if isinstance(name, (bytes, bytearray)):
            name = name.rstrip(b"\x00").decode("utf-8", errors="replace")
        if decimals is not None:
            try:
                decimals = int(decimals)
            except (TypeError, ValueError):
                decimals = None
        return symbol, decimals, name
