export type EventType = "sandwich" | "jit";

export interface MevEvent {
  id: number;
  type: EventType;
  block_number: number;
  block_ts: string;
  extractor_eoa: string;
  extractor_contract: string | null;
  victim_eoa: string | null;
  pool: string;
  gross_profit_wei: string | null;
  gross_profit_token: string | null;
  gas_cost_wei: string | null;
  net_profit_wei: string | null;
  net_profit_usd: string | number | null;
  frontrun_tx: string | null;
  victim_tx: string | null;
  backrun_tx: string | null;
  metadata?: Record<string, unknown>;
  detected_at?: string;
}

export interface LeaderboardEntry {
  address: string;
  attack_count: number;
  total_profit_usd: string | number;
  avg_profit_usd: string | number | null;
}

export interface PoolStat {
  pool: string;
  attack_count: number;
  total_profit_usd: string | number;
}

export interface TimeseriesPoint {
  bucket: string;
  profit_usd: string | number;
  count: number;
}

export interface StatsResponse {
  period: string;
  total_profit_usd: string | number;
  attack_count: number;
  unique_victims: number;
  avg_profit_usd: string | number | null;
  top_pools: PoolStat[];
  timeseries: TimeseriesPoint[];
}

export type Period = "1h" | "24h" | "7d" | "30d";
