"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { LeaderboardEntry, MevEvent, Period, StatsResponse } from "@/lib/types";
import { About } from "@/components/About";
import { EventModal } from "@/components/EventModal";
import { KpiCards } from "@/components/KpiCards";
import { Leaderboard } from "@/components/Leaderboard";
import { LiveFeed } from "@/components/LiveFeed";
import { PeriodToggle } from "@/components/PeriodToggle";
import { ProfitChart } from "@/components/ProfitChart";

export default function Home() {
  const [period, setPeriod] = useState<Period>("24h");
  const [by, setBy] = useState<"profit" | "count">("profit");
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [leaders, setLeaders] = useState<LeaderboardEntry[]>([]);
  const [selected, setSelected] = useState<MevEvent | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);

  // Re-fetch aggregates on period/by change and periodically.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [s, l] = await Promise.all([api.stats(period), api.leaderboard(period, by)]);
        if (!cancelled) {
          setStats(s);
          setLeaders(l);
        }
      } catch {
        // Render stays with stale values — LiveFeed still updates.
      }
    }
    load();
    const t = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [period, by]);

  return (
    <main className="mx-auto max-w-6xl px-4 md:px-6 py-6 space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-3">
          <div className="h-6 w-6 rounded-md bg-gradient-to-br from-emerald-400/80 to-violet-400/60" />
          <div>
            <div className="text-[15px] font-medium tracking-tightish text-zinc-100">
              MEV-Watch
            </div>
            <div className="text-[11px] text-zinc-500 -mt-0.5">
              sandwich &amp; JIT · uniswap v2/v3 · ethereum
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAboutOpen(true)}
            className="text-[11px] text-zinc-400 hover:text-zinc-100 border border-line rounded-md px-2.5 py-1 bg-surface-raised"
          >
            What is this?
          </button>
          <PeriodToggle value={period} onChange={setPeriod} />
        </div>
      </header>

      {/* One-line plain-English framing */}
      <div className="rounded-lg border border-line bg-surface-raised px-4 py-2.5 text-[12.5px] text-zinc-300">
        Every row below is real money a bot took from an ordinary trader's swap on
        Ethereum. Updates live.{" "}
        <button
          onClick={() => setAboutOpen(true)}
          className="text-emerald-300 hover:text-emerald-200 underline underline-offset-2"
        >
          How this works →
        </button>
      </div>

      <KpiCards stats={stats} />

      <ProfitChart data={stats?.timeseries ?? []} />

      <div className="grid md:grid-cols-2 gap-4">
        <Leaderboard entries={leaders} by={by} onByChange={setBy} />
        <LiveFeed onOpen={setSelected} />
      </div>

      <footer className="pt-4 pb-6 text-[11px] text-zinc-600 flex items-center justify-between gap-3 flex-wrap">
        <span>Live API when configured · autonomous demo fallback · updated every 30s</span>
        <div className="flex items-center gap-3">
          <span>
            Built by{" "}
            <a
              href="https://instagram.com/aborisd"
              target="_blank"
              rel="noreferrer"
              className="text-zinc-400 hover:text-zinc-200"
            >
              @aborisd
            </a>{" "}
            ·{" "}
            <a
              href="https://github.com/aborisd"
              target="_blank"
              rel="noreferrer"
              className="text-zinc-400 hover:text-zinc-200"
            >
              github
            </a>
          </span>
          <span className="text-zinc-700">·</span>
          <a href="/docs" className="hover:text-zinc-400">
            API docs →
          </a>
        </div>
      </footer>

      <EventModal event={selected} onClose={() => setSelected(null)} />
      <About open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </main>
  );
}
