import type { NextRequest } from "next/server";

import { demoEvents } from "@/lib/demo-data";
import { json, proxyToLiveApi } from "../_shared";

export async function GET(request: NextRequest) {
  const live = await proxyToLiveApi(request);
  if (live) return live;

  const limit = Number(request.nextUrl.searchParams.get("limit") ?? 50);
  return json(demoEvents(Number.isFinite(limit) ? limit : 50));
}
