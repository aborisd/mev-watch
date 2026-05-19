import type { NextRequest } from "next/server";

import { demoLeaderboard } from "@/lib/demo-data";
import type { Period } from "@/lib/types";
import { json, proxyToLiveApi } from "../_shared";

export async function GET(request: NextRequest) {
  const live = await proxyToLiveApi(request);
  if (live) return live;

  const period = (request.nextUrl.searchParams.get("period") ?? "24h") as Period;
  const by = request.nextUrl.searchParams.get("by") === "count" ? "count" : "profit";
  return json(demoLeaderboard(period, by));
}
