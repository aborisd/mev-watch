from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class EventSummary(BaseModel):
    id: int
    type: str
    block_number: int
    block_ts: datetime
    extractor_eoa: str
    extractor_contract: str | None
    victim_eoa: str | None
    pool: str
    gross_profit_wei: str | None
    gross_profit_token: str | None
    gas_cost_wei: str | None
    net_profit_wei: str | None
    net_profit_usd: Decimal | None
    frontrun_tx: str | None
    victim_tx: str | None
    backrun_tx: str | None


class EventDetail(EventSummary):
    metadata: dict[str, Any] | None
    detected_at: datetime


class LeaderboardEntry(BaseModel):
    address: str
    attack_count: int
    total_profit_usd: Decimal
    avg_profit_usd: Decimal | None


class PoolStat(BaseModel):
    pool: str
    attack_count: int
    total_profit_usd: Decimal


class TimeseriesPoint(BaseModel):
    bucket: datetime
    profit_usd: Decimal
    count: int


class StatsResponse(BaseModel):
    period: str
    total_profit_usd: Decimal
    attack_count: int
    unique_victims: int
    avg_profit_usd: Decimal | None
    top_pools: list[PoolStat]
    timeseries: list[TimeseriesPoint]


class AddressProfile(BaseModel):
    address: str
    total_attacks: int
    total_profit_usd: Decimal
    top_pools: list[PoolStat]
    recent_events: list[EventSummary]
