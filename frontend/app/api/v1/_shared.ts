import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function json(data: unknown, init?: ResponseInit) {
  return Response.json(data, {
    ...init,
    headers: {
      "Cache-Control": "no-store",
      ...(init?.headers ?? {}),
    },
  });
}

export async function proxyToLiveApi(request: NextRequest): Promise<Response | null> {
  const base = process.env.API_INTERNAL_URL || process.env.LIVE_API_BASE;
  if (!base) return null;

  const target = new URL(request.nextUrl.pathname + request.nextUrl.search, base);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1200);
  try {
    const response = await fetch(target, {
      headers: { accept: request.headers.get("accept") ?? "application/json" },
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) return null;
    return response;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}
