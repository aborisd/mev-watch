"""Well-known topic hashes, addresses, and protocol constants."""

# ─── Event topic hashes (keccak of canonical signature) ───
# Uniswap V2: Swap(address,uint256,uint256,uint256,uint256,address)
V2_SWAP_TOPIC = bytes.fromhex("d78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822")
# Uniswap V3: Swap(address,address,int256,int256,uint160,uint128,int24)
V3_SWAP_TOPIC = bytes.fromhex("c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67")
# Uniswap V3: Mint(address,address,int24,int24,uint128,uint256,uint256)
V3_MINT_TOPIC = bytes.fromhex("7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde")
# Uniswap V3: Burn(address,int24,int24,uint128,uint256,uint256)
V3_BURN_TOPIC = bytes.fromhex("0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c")

ALL_TOPICS = [V2_SWAP_TOPIC, V3_SWAP_TOPIC, V3_MINT_TOPIC, V3_BURN_TOPIC]

# ─── Well-known token addresses ───
WETH = bytes.fromhex("c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
USDC = bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
USDT = bytes.fromhex("dac17f958d2ee523a2206206994597c13d831ec7")
DAI = bytes.fromhex("6b175474e89094c44da98b954eedeac495271d0f")

STABLES = {USDC, USDT, DAI}

# ─── Reference pools ───
# Uniswap V3 USDC/WETH 0.05% — primary ETH/USD price source
USDC_WETH_V3_POOL = bytes.fromhex("88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

USDC_DECIMALS = 6
WETH_DECIMALS = 18

# ─── Protocol identifiers ───
PROTO_V2 = "uni_v2"
PROTO_V3 = "uni_v3"
