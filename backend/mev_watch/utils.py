"""Conversion helpers for addresses, hashes, and numeric types."""

from decimal import Decimal
from typing import Any


def to_bytes(hex_or_bytes: str | bytes | bytearray | memoryview | None) -> bytes | None:
    """Coerce a 0x-hex string or bytes-like into bytes. Passes None through."""
    if hex_or_bytes is None:
        return None
    if isinstance(hex_or_bytes, (bytes, bytearray, memoryview)):
        return bytes(hex_or_bytes)
    s = hex_or_bytes
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    return bytes.fromhex(s)


def addr(b: bytes | None) -> str | None:
    """Format a 20-byte address as 0x-hex. Returns None for None."""
    if b is None:
        return None
    return "0x" + b.hex()


def tx_hex(b: bytes | None) -> str | None:
    return addr(b)


def hexint(x: Any) -> int:
    """Parse an int from a hex string or pass through an int."""
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        return int(x, 16) if x.startswith(("0x", "0X")) else int(x)
    raise TypeError(f"Cannot convert {type(x).__name__} to int")


def wei_to_eth(wei: int | Decimal) -> Decimal:
    return Decimal(wei) / Decimal(10**18)


def wei_to_usd(wei: int | Decimal, eth_price_usd: Decimal) -> Decimal:
    """Convert WETH-denominated wei to USD using an ETH/USD price."""
    return wei_to_eth(wei) * eth_price_usd


def address_from_topic(topic: bytes) -> bytes:
    """Event topics pad addresses to 32 bytes; take the low 20."""
    if len(topic) != 32:
        raise ValueError(f"Expected 32-byte topic, got {len(topic)}")
    return topic[12:]


def signed_int256(u: int) -> int:
    """Reinterpret an unsigned 256-bit integer as signed (two's complement)."""
    if u >= 2**255:
        return u - 2**256
    return u
