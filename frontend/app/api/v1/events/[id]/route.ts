import type { NextRequest } from "next/server";

import { demoEvents } from "@/lib/demo-data";
import { json, proxyToLiveApi } from "../../_shared";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const live = await proxyToLiveApi(request);
  if (live) return live;

  const { id: rawId } = await params;
  const id = Number(rawId);
  const event = demoEvents(100).find((row) => row.id === id);
  if (!event) return json({ detail: "Event not found" }, { status: 404 });
  return json(event);
}
