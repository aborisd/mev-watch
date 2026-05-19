"""Decode Uniswap V2/V3 event logs into typed dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eth_abi import decode as abi_decode

from ..constants import V2_SWAP_TOPIC, V3_BURN_TOPIC, V3_MINT_TOPIC, V3_SWAP_TOPIC
from ..utils import address_from_topic, to_bytes


@dataclass(slots=True)
class SwapLog:
    tx_hash: bytes
    log_index: int
    tx_index: int
    pool: bytes
    protocol: str            # 'uni_v2' | 'uni_v3'
    event_sender: bytes      # msg.sender of Swap event (often a router)
    recipient: bytes
    # V2: amount0In/amount1In/amount0Out/amount1Out — exactly one In > 0 and one Out > 0.
    # V3: amount0/amount1 — signed; positive = into pool, negative = out of pool.
    amount0_in: int = 0
    amount1_in: int = 0
    amount0_out: int = 0
    amount1_out: int = 0
    amount0: int = 0
    amount1: int = 0


@dataclass(slots=True)
class LiquidityLog:
    tx_hash: bytes
    log_index: int
    tx_index: int
    pool: bytes
    event_type: str          # 'mint' | 'burn'
    owner: bytes
    tick_lower: int
    tick_upper: int
    liquidity: int
    amount0: int | None
    amount1: int | None


# ─── normalisation helpers ─────────────────────────────────────────

def _b(v: Any) -> bytes:
    if isinstance(v, (bytes, bytearray, memoryview)):
        return bytes(v)
    return to_bytes(v) or b""


def _i(v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 16) if v.startswith(("0x", "0X")) else int(v)
    raise TypeError(f"Cannot int-ify {type(v)}")


def _topics(log: dict[str, Any]) -> list[bytes]:
    return [_b(t) for t in log["topics"]]


def _data(log: dict[str, Any]) -> bytes:
    return _b(log["data"])


def _int24_signed(topic: bytes) -> int:
    n = int.from_bytes(topic, "big")
    if n >= 2**255:
        n -= 2**256
    return n


# ─── decoders ─────────────────────────────────────────────────────

def decode_v2_swap(log: dict[str, Any], tx_index: int) -> SwapLog:
    topics = _topics(log)
    a0i, a1i, a0o, a1o = abi_decode(
        ["uint256", "uint256", "uint256", "uint256"], _data(log)
    )
    return SwapLog(
        tx_hash=_b(log["transactionHash"]),
        log_index=_i(log["logIndex"]),
        tx_index=tx_index,
        pool=_b(log["address"]),
        protocol="uni_v2",
        event_sender=address_from_topic(topics[1]),
        recipient=address_from_topic(topics[2]),
        amount0_in=int(a0i),
        amount1_in=int(a1i),
        amount0_out=int(a0o),
        amount1_out=int(a1o),
    )


def decode_v3_swap(log: dict[str, Any], tx_index: int) -> SwapLog:
    topics = _topics(log)
    a0, a1, _sqrt, _liq, _tick = abi_decode(
        ["int256", "int256", "uint160", "uint128", "int24"], _data(log)
    )
    return SwapLog(
        tx_hash=_b(log["transactionHash"]),
        log_index=_i(log["logIndex"]),
        tx_index=tx_index,
        pool=_b(log["address"]),
        protocol="uni_v3",
        event_sender=address_from_topic(topics[1]),
        recipient=address_from_topic(topics[2]),
        amount0=int(a0),
        amount1=int(a1),
    )


def decode_v3_mint(log: dict[str, Any], tx_index: int) -> LiquidityLog:
    topics = _topics(log)
    _sender, amount, amount0, amount1 = abi_decode(
        ["address", "uint128", "uint256", "uint256"], _data(log)
    )
    return LiquidityLog(
        tx_hash=_b(log["transactionHash"]),
        log_index=_i(log["logIndex"]),
        tx_index=tx_index,
        pool=_b(log["address"]),
        event_type="mint",
        owner=address_from_topic(topics[1]),
        tick_lower=_int24_signed(topics[2]),
        tick_upper=_int24_signed(topics[3]),
        liquidity=int(amount),
        amount0=int(amount0),
        amount1=int(amount1),
    )


def decode_v3_burn(log: dict[str, Any], tx_index: int) -> LiquidityLog:
    topics = _topics(log)
    amount, amount0, amount1 = abi_decode(
        ["uint128", "uint256", "uint256"], _data(log)
    )
    return LiquidityLog(
        tx_hash=_b(log["transactionHash"]),
        log_index=_i(log["logIndex"]),
        tx_index=tx_index,
        pool=_b(log["address"]),
        event_type="burn",
        owner=address_from_topic(topics[1]),
        tick_lower=_int24_signed(topics[2]),
        tick_upper=_int24_signed(topics[3]),
        liquidity=int(amount),
        amount0=int(amount0),
        amount1=int(amount1),
    )


def decode_log(log: dict[str, Any], tx_index: int) -> SwapLog | LiquidityLog | None:
    topics = log.get("topics") or []
    if not topics:
        return None
    topic0 = _b(topics[0])
    if topic0 == V2_SWAP_TOPIC:
        return decode_v2_swap(log, tx_index)
    if topic0 == V3_SWAP_TOPIC:
        return decode_v3_swap(log, tx_index)
    if topic0 == V3_MINT_TOPIC:
        return decode_v3_mint(log, tx_index)
    if topic0 == V3_BURN_TOPIC:
        return decode_v3_burn(log, tx_index)
    return None


__all__ = ["SwapLog", "LiquidityLog", "decode_log"]
