from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from ..db import get_pool
from ..logging import get_logger
from ..utils import to_bytes
from .queries import (
    EVENT_COLS,
    SQL_ADDRESS_EVENTS,
    SQL_ADDRESS_POOLS,
    SQL_ADDRESS_STATS,
    SQL_EVENT_DETAIL,
    SQL_LEADERBOARD,
    SQL_LIST_EVENTS_BASE,
    SQL_STATS,
    SQL_TIMESERIES,
    SQL_TOP_POOLS,
    bucket_for_period,
    period_to_interval,
)
from .schemas import (
    AddressProfile,
    EventDetail,
    EventSummary,
    LeaderboardEntry,
    PoolStat,
    StatsResponse,
    TimeseriesPoint,
)

router = APIRouter()
log = get_logger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────

def _hex(b: bytes | None) -> str | None:
    if b is None:
        return None
    return "0x" + bytes(b).hex()


def _wei(x) -> str | None:
    if x is None:
        return None
    return str(x)


def _row_to_event(row: Any, detail: bool = False) -> dict:
    d = {
        "id": row["id"],
        "type": row["event_type"],
        "block_number": row["block_number"],
        "block_ts": row["block_ts"],
        "extractor_eoa": _hex(row["extractor_eoa"]),
        "extractor_contract": _hex(row["extractor_contract"]),
        "victim_eoa": _hex(row["victim_eoa"]),
        "pool": _hex(row["pool"]),
        "gross_profit_wei": _wei(row["gross_profit_wei"]),
        "gross_profit_token": _hex(row["gross_profit_token"]),
        "gas_cost_wei": _wei(row["gas_cost_wei"]),
        "net_profit_wei": _wei(row["net_profit_wei"]),
        "net_profit_usd": row["net_profit_usd"],
        "frontrun_tx": _hex(row["frontrun_tx"]),
        "victim_tx": _hex(row["victim_tx"]),
        "backrun_tx": _hex(row["backrun_tx"]),
    }
    if detail:
        meta = row["metadata"]
        if isinstance(meta, (bytes, str)):
            try:
                meta = json.loads(meta) if isinstance(meta, str) else json.loads(meta.decode())
            except Exception:  # noqa: BLE001
                meta = None
        d["metadata"] = meta
        d["detected_at"] = row["detected_at"]
    return d


def _parse_address(addr: str) -> bytes:
    b = to_bytes(addr)
    if b is None or len(b) != 20:
        raise HTTPException(status_code=400, detail="Invalid Ethereum address")
    return b


# ─── Endpoints ────────────────────────────────────────────────────

@router.get("/events", response_model=list[EventSummary])
async def list_events(
    type: str | None = Query(None, pattern="^(sandwich|jit)$"),
    min_profit_usd: float | None = Query(None, ge=0),
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=500),
    before: int | None = None,
):
    """List MEV events with filters and cursor pagination (cursor = event id)."""
    clauses: list[str] = []
    params: list[Any] = []
    n = 0
    if type is not None:
        n += 1
        clauses.append(f"AND event_type = ${n}")
        params.append(type)
    if min_profit_usd is not None:
        n += 1
        clauses.append(f"AND net_profit_usd >= ${n}")
        params.append(min_profit_usd)
    if since is not None:
        n += 1
        clauses.append(f"AND block_ts >= ${n}")
        params.append(since)
    if before is not None:
        n += 1
        clauses.append(f"AND id < ${n}")
        params.append(before)
    n += 1
    params.append(limit)
    sql = SQL_LIST_EVENTS_BASE + " " + " ".join(clauses) + f" ORDER BY id DESC LIMIT ${n}"

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [_row_to_event(r) for r in rows]


@router.get("/events/stream")
async def stream_events():
    """Server-Sent Events feed of new MEV events (via Postgres NOTIFY)."""
    pool = await get_pool()

    async def generator():
        conn = await pool.acquire()
        queue: asyncio.Queue[int] = asyncio.Queue(maxsize=1000)

        def _on_notify(_c, _pid, _chan, payload):
            try:
                queue.put_nowait(int(payload))
            except Exception:  # noqa: BLE001
                pass

        await conn.add_listener("mev_events_new", _on_notify)
        try:
            while True:
                try:
                    event_id = await asyncio.wait_for(queue.get(), timeout=15.0)
                    row = await conn.fetchrow(SQL_EVENT_DETAIL, event_id)
                    if row is None:
                        continue
                    yield {
                        "event": "mev",
                        "data": json.dumps(_row_to_event(row, detail=True), default=str),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            try:
                await conn.remove_listener("mev_events_new", _on_notify)
            except Exception:  # noqa: BLE001
                pass
            await pool.release(conn)

    return EventSourceResponse(generator())


@router.get("/events/{event_id}", response_model=EventDetail)
async def get_event(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(SQL_EVENT_DETAIL, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _row_to_event(row, detail=True)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    period: str = Query("24h", pattern="^(1h|24h|7d|30d)$"),
    by: str = Query("profit", pattern="^(profit|count)$"),
    type: str | None = Query(None, pattern="^(sandwich|jit)$"),
):
    interval = period_to_interval(period)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(SQL_LEADERBOARD, interval, type, by)
    return [
        {
            "address": _hex(r["address"]),
            "attack_count": r["attack_count"],
            "total_profit_usd": r["total_profit_usd"],
            "avg_profit_usd": r["avg_profit_usd"],
        }
        for r in rows
    ]


@router.get("/stats", response_model=StatsResponse)
async def stats(
    period: str = Query("24h", pattern="^(1h|24h|7d|30d)$"),
):
    interval = period_to_interval(period)
    bucket = bucket_for_period(period)

    pool = await get_pool()
    async with pool.acquire() as conn:
        stats_row = await conn.fetchrow(SQL_STATS, interval)
        pool_rows = await conn.fetch(SQL_TOP_POOLS, interval)
        ts_rows = await conn.fetch(SQL_TIMESERIES, interval, bucket)

    return {
        "period": period,
        "total_profit_usd": stats_row["total_profit_usd"],
        "attack_count": stats_row["attack_count"],
        "unique_victims": stats_row["unique_victims"],
        "avg_profit_usd": stats_row["avg_profit_usd"],
        "top_pools": [
            {
                "pool": _hex(r["pool"]),
                "attack_count": r["attack_count"],
                "total_profit_usd": r["total_profit_usd"],
            }
            for r in pool_rows
        ],
        "timeseries": [
            {
                "bucket": r["bucket"],
                "profit_usd": r["profit_usd"],
                "count": r["count"],
            }
            for r in ts_rows
        ],
    }


@router.get("/address/{address}", response_model=AddressProfile)
async def address_profile(address: str):
    addr_bytes = _parse_address(address)
    pool = await get_pool()
    async with pool.acquire() as conn:
        stat_row = await conn.fetchrow(SQL_ADDRESS_STATS, addr_bytes)
        pool_rows = await conn.fetch(SQL_ADDRESS_POOLS, addr_bytes)
        event_rows = await conn.fetch(SQL_ADDRESS_EVENTS, addr_bytes, 25)

    return {
        "address": address.lower(),
        "total_attacks": stat_row["attack_count"],
        "total_profit_usd": stat_row["total_profit_usd"],
        "top_pools": [
            {
                "pool": _hex(r["pool"]),
                "attack_count": r["attack_count"],
                "total_profit_usd": r["total_profit_usd"],
            }
            for r in pool_rows
        ],
        "recent_events": [_row_to_event(r) for r in event_rows],
    }


@router.get("/health")
async def health():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"ok": True}
