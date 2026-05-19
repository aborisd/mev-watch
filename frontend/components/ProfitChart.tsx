"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fmtUsd } from "@/lib/format";
import type { TimeseriesPoint } from "@/lib/types";
import { Card, CardBody, CardHeader, CardTitle } from "./ui/Card";

export function ProfitChart({ data }: { data: TimeseriesPoint[] }) {
  const rows = data.map((d) => ({
    bucket: d.bucket,
    ts: new Date(d.bucket).getTime(),
    profit: Number(d.profit_usd ?? 0),
    count: d.count,
  }));

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Profit over time</CardTitle>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            USD extracted per bucket · higher spikes = bigger hits
          </div>
        </div>
      </CardHeader>
      <CardBody className="h-[220px] px-0 pr-1 pb-1 pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ left: 8, right: 12, top: 4, bottom: 4 }}>
            <defs>
              <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4ade80" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="2 2" vertical={false} />
            <XAxis
              dataKey="ts"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) =>
                new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              }
              stroke="#3a3a3a"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              minTickGap={40}
            />
            <YAxis
              width={50}
              tickFormatter={(v) => fmtUsd(v, 0)}
              stroke="#3a3a3a"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{ background: "#111", border: "1px solid #222", borderRadius: 8 }}
              labelStyle={{ color: "#a1a1aa", fontSize: 11 }}
              itemStyle={{ color: "#fafafa", fontSize: 12 }}
              labelFormatter={(v) => new Date(Number(v)).toLocaleString()}
              formatter={(val: number | string, k) =>
                k === "profit" ? [fmtUsd(val), "profit"] : [val, String(k)]
              }
            />
            <Area
              type="monotone"
              dataKey="profit"
              stroke="#4ade80"
              strokeWidth={1.5}
              fill="url(#g)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardBody>
    </Card>
  );
}
