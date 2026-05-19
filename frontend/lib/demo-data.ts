import type {
  EventType,
  LeaderboardEntry,
  MevEvent,
  Period,
  StatsResponse,
  TimeseriesPoint,
} from "./types";

const extractors = [
  "0x4a2f7d9b6c83e1f25a4c9a7d81f0c5b6a3e9d128",
  "0x9c91f84e2aab3f0d7e5c46b123f0a5c28a87e991",
  "0x2b17a47db8f8c512ce9e8a16a223bb7d1a7c09ef",
  "0x6d4e913a0f74c0c6b89aa977819fb2d2dd3a510a",
  "0x82f8c6c78a5b9b061eb8f136c2dcb926d1f72b2d",
  "0x19a02f6a89e67e5a8cc9c74b6d11b0d6ac813777",
];

const pools = [
  "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
  "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
  "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed",
  "0x5777d92f208679db4b9778590fa3cab3ac9e2168",
  "0x60594a405d53811d3bc4766596efd80fd545a270",
];

const victims = [
  "0xf14b9e7165c44183ad5fbd8cc04c62e35d9a42f9",
  "0x36f3f7f020bf7956f4a19c18b9d40ea58284e22a",
  "0xa6c178d3c7f2a13e4d8fc65d8b40b09f03a71e90",
  "0x0bdc81880b35123a48c109d9dbb9a66deef3db02",
  "0x7c4e8f2b7d29a510f8dd8a2a2baf8bfa04c2d355",
];

const tx = (seed: number) => "0x" + seed.toString(16).padStart(64, "0").slice(0, 64);

function periodMs(period: Period): number {
  return {
    "1h": 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
    "30d": 30 * 24 * 60 * 60 * 1000,
  }[period];
}

function bucketCount(period: Period): number {
  return period === "1h" ? 12 : period === "24h" ? 24 : period === "7d" ? 28 : 30;
}

export function demoEvents(limit = 80): MevEvent[] {
  const now = Date.now();
  return Array.from({ length: Math.max(limit, 80) }, (_, i) => {
    const type: EventType = i % 5 === 0 ? "jit" : "sandwich";
    const blockNumber = 19987342 - i * 2;
    const profit = Math.round((18 + (i % 13) * 11 + Math.sin(i / 2) * 14) * 100) / 100;
    const baseIndex = 40 + (i % 120);
    return {
      id: 10000 - i,
      type,
      block_number: blockNumber,
      block_ts: new Date(now - i * 3 * 60 * 1000).toISOString(),
      extractor_eoa: extractors[i % extractors.length],
      extractor_contract: i % 3 === 0 ? null : extractors[(i + 2) % extractors.length],
      victim_eoa: victims[i % victims.length],
      pool: pools[i % pools.length],
      gross_profit_wei: String(BigInt(Math.floor((profit + 4) * 1e15))),
      gross_profit_token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      gas_cost_wei: String(BigInt(Math.floor(4 * 1e15))),
      net_profit_wei: String(BigInt(Math.floor(profit * 1e15))),
      net_profit_usd: profit,
      frontrun_tx: tx(100000 + i * 3),
      victim_tx: tx(100001 + i * 3),
      backrun_tx: tx(100002 + i * 3),
      metadata:
        type === "sandwich"
          ? {
              front_tx_index: baseIndex,
              victim_tx_index: baseIndex + 1,
              back_tx_index: baseIndex + 2,
            }
          : {
              mint_tx_index: baseIndex,
              victim_tx_index: baseIndex + 3,
              burn_tx_index: baseIndex + 7,
            },
      detected_at: new Date(now - i * 3 * 60 * 1000 + 8000).toISOString(),
    };
  }).slice(0, limit);
}

export function demoStats(period: Period): StatsResponse {
  const count = bucketCount(period);
  const now = Date.now();
  const span = periodMs(period);
  const step = span / count;
  const timeseries: TimeseriesPoint[] = Array.from({ length: count }, (_, i) => {
    const value = 220 + Math.sin(i / 2) * 95 + (i % 6) * 35 + (i === count - 5 ? 680 : 0);
    return {
      bucket: new Date(now - span + i * step).toISOString(),
      profit_usd: Math.max(18, Math.round(value * 100) / 100),
      count: 4 + (i % 9),
    };
  });
  const total = timeseries.reduce((sum, row) => sum + Number(row.profit_usd), 0);
  const attacks = timeseries.reduce((sum, row) => sum + row.count, 0);
  return {
    period,
    total_profit_usd: Math.round(total * 100) / 100,
    attack_count: attacks,
    unique_victims: Math.round(attacks * 0.72),
    avg_profit_usd: Math.round((total / attacks) * 100) / 100,
    top_pools: pools.slice(0, 5).map((pool, i) => ({
      pool,
      attack_count: Math.max(4, Math.round(attacks / (i + 4))),
      total_profit_usd: Math.round((total / (i + 2.4)) * 100) / 100,
    })),
    timeseries,
  };
}

export function demoLeaderboard(period: Period, by: "profit" | "count"): LeaderboardEntry[] {
  const multiplier = period === "1h" ? 0.15 : period === "24h" ? 1 : period === "7d" ? 5.6 : 18;
  const rows = extractors.map((address, i) => {
    const attackCount = Math.round((72 - i * 7) * multiplier);
    const totalProfit = Math.round((7800 / (i + 1.6)) * multiplier * 100) / 100;
    return {
      address,
      attack_count: Math.max(1, attackCount),
      total_profit_usd: totalProfit,
      avg_profit_usd: Math.round((totalProfit / Math.max(1, attackCount)) * 100) / 100,
    };
  });
  return rows.sort((a, b) =>
    by === "count"
      ? b.attack_count - a.attack_count
      : Number(b.total_profit_usd) - Number(a.total_profit_usd),
  );
}
