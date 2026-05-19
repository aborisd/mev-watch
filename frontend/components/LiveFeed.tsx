"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { fmtUsd, relTime, shortAddr } from "@/lib/format";
import type { MevEvent } from "@/lib/types";
import { Card, CardBody, CardHeader, CardTitle } from "./ui/Card";
import { Badge } from "./ui/Badge";

const MAX_FEED = 80;

export function LiveFeed({ onOpen }: { onOpen: (e: MevEvent) => void }) {
  const [events, setEvents] = useState<MevEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const tickRef = useRef(0);
  const [, forceTick] = useState(0);

  // Initial load + SSE subscription
  useEffect(() => {
    let cancelled = false;
    api.events(40).then((rows) => {
      if (!cancelled) setEvents(rows);
    });

    const base = process.env.NEXT_PUBLIC_API_BASE ?? "";
    const es = new EventSource(`${base}/api/v1/events/stream`);

    es.addEventListener("mev", (ev) => {
      try {
        const e = JSON.parse((ev as MessageEvent).data) as MevEvent;
        setEvents((prev) => {
          if (prev.some((p) => p.id === e.id)) return prev;
          return [e, ...prev].slice(0, MAX_FEED);
        });
      } catch {}
    });
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    const tick = setInterval(() => {
      tickRef.current += 1;
      forceTick(tickRef.current);
    }, 10_000);

    return () => {
      cancelled = true;
      clearInterval(tick);
      es.close();
    };
  }, []);

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div>
          <CardTitle>Live feed</CardTitle>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            Each row = a real swap that got attacked · click for details
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500">
          <span
            className={
              "inline-block h-1.5 w-1.5 rounded-full " +
              (connected ? "bg-emerald-400 animate-pulse" : "bg-zinc-600")
            }
          />
          {connected ? "live" : "reconnecting"}
        </div>
      </CardHeader>
      <CardBody className="p-0">
        <ul className="max-h-[560px] overflow-y-auto divide-y divide-line/60">
          {events.length === 0 && (
            <li className="text-center text-zinc-500 py-10 text-[12px]">
              Waiting for events…
            </li>
          )}
          {events.map((e) => (
            <li
              key={e.id}
              onClick={() => onOpen(e)}
              className="fade-in px-4 py-2.5 cursor-pointer hover:bg-white/[0.02] flex items-center justify-between gap-3"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Badge variant={e.type === "sandwich" ? "sandwich" : "jit"}>
                  {e.type}
                </Badge>
                <div className="min-w-0">
                  <div className="num text-zinc-100 text-[13px]">
                    {fmtUsd(e.net_profit_usd)}
                  </div>
                  <div className="mono text-[11px] text-zinc-500 truncate">
                    {shortAddr(e.extractor_eoa)} · block {e.block_number.toLocaleString()}
                  </div>
                </div>
              </div>
              <div className="text-[11px] text-zinc-500 num tabular-nums shrink-0">
                {relTime(e.block_ts)}
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}
