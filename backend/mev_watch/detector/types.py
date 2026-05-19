"""Shared dataclasses for the detector (decoupled from ingester schemas)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class DetectSwap:
    tx_hash: bytes
    log_index: int
    tx_index: int
    block_number: int
    block_ts: datetime
    pool: bytes
    protocol: str
    sender: bytes              # EOA that signed the tx
    tx_to: bytes | None        # contract called by the tx (often a bot)
    recipient: bytes           # recipient of token_out (from event)
    token_in: bytes
    token_out: bytes
    amount_in: int
    amount_out: int
    gas_used: int
    gas_price: int


@dataclass(slots=True)
class DetectLiq:
    tx_hash: bytes
    log_index: int
    tx_index: int
    block_number: int
    block_ts: datetime
    pool: bytes
    event_type: str            # 'mint' | 'burn'
    owner: bytes
    tick_lower: int
    tick_upper: int
    liquidity: int
    amount0: int
    amount1: int
    sender: bytes              # EOA that signed the tx
    tx_to: bytes | None
    gas_used: int
    gas_price: int


@dataclass(slots=True)
class SandwichCandidate:
    pool: bytes
    front: DetectSwap
    victim: DetectSwap
    back: DetectSwap


@dataclass(slots=True)
class JITCandidate:
    pool: bytes
    mint: DetectLiq
    burn: DetectLiq
    victim: DetectSwap
