// Relative URLs — Next.js rewrites /api/* to the API service in prod/dev-docker.
// In plain `next dev`, set NEXT_PUBLIC_API_BASE=http://localhost:8001.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function j<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

import type {
  LeaderboardEntry,
  MevEvent,
  Period,
  StatsResponse,
} from "./types";

export const api = {
  stats: (period: Period) => j<StatsResponse>(`/api/v1/stats?period=${period}`),
  leaderboard: (period: Period, by: "profit" | "count" = "profit") =>
    j<LeaderboardEntry[]>(`/api/v1/leaderboard?period=${period}&by=${by}`),
  events: (limit = 50) => j<MevEvent[]>(`/api/v1/events?limit=${limit}`),
  event: (id: number) => j<MevEvent>(`/api/v1/events/${id}`),
};
