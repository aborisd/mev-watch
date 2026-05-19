"""Derive ETH/USD price from Uniswap V3 USDC/WETH 0.05% pool slot0()."""

from __future__ import annotations

from decimal import Decimal, getcontext

from web3 import AsyncWeb3

from ..abi import V3_POOL_ABI
from ..constants import USDC_WETH_V3_POOL
from ..logging import get_logger
from ..rpc import with_retry
from ..utils import addr

log = get_logger(__name__)
getcontext().prec = 60

# In this pool, token0 = USDC (6 decimals), token1 = WETH (18 decimals).
# sqrtPriceX96 encodes sqrt(token1/token0 raw ratio) * 2^96.
# price_token1_per_token0_raw = (sqrtPriceX96 / 2^96) ** 2
# decimal-adjusted price of WETH in USDC = raw * 10^(dec0 - dec1) = raw * 10^-12
# We want USDC per WETH = 1 / above = 10^12 / raw
_DEC_ADJ = Decimal(10) ** 12
_TWO_96 = Decimal(2) ** 96


async def fetch_eth_usd_price(w3: AsyncWeb3, block_number: int) -> Decimal | None:
    """Query slot0() on USDC/WETH 0.05% pool at a given block. Returns USD per WETH."""
    try:
        checksum = w3.to_checksum_address(addr(USDC_WETH_V3_POOL))
        contract = w3.eth.contract(address=checksum, abi=V3_POOL_ABI)
        slot0 = await with_retry(
            lambda: contract.functions.slot0().call(block_identifier=block_number)
        )
        sqrt_price = Decimal(slot0[0])
        if sqrt_price == 0:
            return None
        raw = (sqrt_price / _TWO_96) ** 2
        return _DEC_ADJ / raw
    except Exception as e:  # noqa: BLE001
        log.debug("eth_usd_price_failed", block=block_number, err=str(e))
        return None


async def write_eth_usd_price(db_pool, block_number: int, price: Decimal) -> None:
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO eth_usd_prices (block_number, price_usd)
            VALUES ($1, $2)
            ON CONFLICT (block_number) DO UPDATE SET price_usd = EXCLUDED.price_usd
            """,
            block_number, price,
        )
