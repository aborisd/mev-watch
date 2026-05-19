import type { NextRequest } from "next/server";

import { demoEvents } from "@/lib/demo-data";
import { proxyToLiveApi } from "../../_shared";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const live = await proxyToLiveApi(request);
  if (live) return live;

  const encoder = new TextEncoder();
  let i = 0;
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode("event: ping\ndata: {}\n\n"));
      const timer = setInterval(() => {
        const event = demoEvents(20)[i % 20];
        controller.enqueue(
          encoder.encode(`event: mev\ndata: ${JSON.stringify({ ...event, id: Date.now() })}\n\n`),
        );
        i += 1;
      }, 6500);

      request.signal.addEventListener("abort", () => {
        clearInterval(timer);
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
