"""Profit math: gross, gas cost, net, USD conversion. Bribe = 0 in MVP."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..constants import DAI, USDC, USDT, WETH

# Decimals for tokens we can price without an external oracle.
STABLE_DECIMALS: dict[bytes, int] = {
    USDC: 6,
    USDT: 6,
    DAI: 18,
}
WETH_DECIMALS = 18


@dataclass(slots=True)
class Economics:
    gross_profit_wei: int | None
    gross_profit_token: bytes | None
    gas_cost_wei: int
    net_profit_wei: int | None      # in WETH wei
    net_profit_usd: Decimal | None
    quote_unavailable: bool = False


async def get_eth_price(db_pool, block_number: int) -> Decimal | None:
    """Nearest ETH/USD price snapshot at or before given block."""
    async with db_pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT price_usd FROM eth_usd_prices
            WHERE block_number <= $1
            ORDER BY block_number DESC
            LIMIT 1
            """,
            block_number,
        )


def _to_weth_wei(token: bytes, amount: int, eth_price_usd: Decimal | None) -> int | None:
    """Convert `amount` of `token` into WETH wei. Returns None if not priceable."""
    if token == WETH:
        return amount
    if token in STABLE_DECIMALS:
        if eth_price_usd is None or eth_price_usd == 0:
            return None
        dec = STABLE_DECIMALS[token]
        usd = Decimal(amount) / Decimal(10) ** dec
        weth = usd / eth_price_usd
        return int(weth * (Decimal(10) ** WETH_DECIMALS))
    return None


def _weth_wei_to_usd(weth_wei: int | None, eth_price_usd: Decimal | None) -> Decimal | None:
    if weth_wei is None or eth_price_usd is None:
        return None
    return (Decimal(weth_wei) / (Decimal(10) ** WETH_DECIMALS)) * eth_price_usd


async def sandwich_economics(db_pool, front_gas_wei: int, back_gas_wei: int,
                              gross_profit_token: bytes, gross_profit_wei: int,
                              block_number: int) -> Economics:
    eth_price = await get_eth_price(db_pool, block_number)
    gross_weth = _to_weth_wei(gross_profit_token, gross_profit_wei, eth_price)
    gas_cost_wei = front_gas_wei + back_gas_wei
    net_weth = None
    if gross_weth is not None:
        net_weth = gross_weth - gas_cost_wei
    net_usd = _weth_wei_to_usd(net_weth, eth_price)
    return Economics(
        gross_profit_wei=gross_profit_wei,
        gross_profit_token=gross_profit_token,
        gas_cost_wei=gas_cost_wei,
        net_profit_wei=net_weth,
        net_profit_usd=net_usd,
        quote_unavailable=(gross_weth is None),
    )


async def jit_economics(db_pool,
                         victim_token_in: bytes,
                         victim_amount_in: int,
                         fee_tier: int | None,
                         mint_gas_wei: int,
                         burn_gas_wei: int,
                         block_number: int) -> Economics:
    """JIT profit ≈ victim.amount_in × fee_tier / 1_000_000, in victim.token_in.

    V3 fees accrue to LPs proportional to their liquidity share in the swap's tick
    range. A JIT position that provides all liquidity in a tight range around the
    current tick captures (approximately) all of the fee paid by the victim swap.
    The true capture ratio is <1 if other LPs exist in the same range — this is an
    upper bound and documented in README.
    """
    eth_price = await get_eth_price(db_pool, block_number)
    gas_cost_wei = mint_gas_wei + burn_gas_wei

    if fee_tier is None or fee_tier <= 0:
        return Economics(
            gross_profit_wei=None,
            gross_profit_token=victim_token_in,
            gas_cost_wei=gas_cost_wei,
            net_profit_wei=None,
            net_profit_usd=None,
            quote_unavailable=True,
        )

    gross_token_amount = victim_amount_in * fee_tier // 1_000_000
    gross_weth = _to_weth_wei(victim_token_in, gross_token_amount, eth_price)
    net_weth = (gross_weth - gas_cost_wei) if gross_weth is not None else None
    net_usd = _weth_wei_to_usd(net_weth, eth_price)
    return Economics(
        gross_profit_wei=gross_token_amount,
        gross_profit_token=victim_token_in,
        gas_cost_wei=gas_cost_wei,
        net_profit_wei=net_weth,
        net_profit_usd=net_usd,
        quote_unavailable=(gross_weth is None),
    )
