import { Card, CardBody, CardTitle } from "./ui/Card";
import { fmtInt, fmtUsd } from "@/lib/format";
import type { StatsResponse } from "@/lib/types";

export function KpiCards({ stats }: { stats: StatsResponse | null }) {
  const items = [
    {
      label: "Total Profit",
      value: stats ? fmtUsd(stats.total_profit_usd) : "—",
      hint: "Money bots took from traders in the selected period",
    },
    {
      label: "Attacks",
      value: stats ? fmtInt(stats.attack_count) : "—",
      hint: "Number of detected sandwich + JIT events",
    },
    {
      label: "Unique Victims",
      value: stats ? fmtInt(stats.unique_victims) : "—",
      hint: "Distinct wallets that lost money",
    },
    {
      label: "Avg Profit",
      value: stats ? fmtUsd(stats.avg_profit_usd) : "—",
      hint: "Per attack — how hard an average victim was hit",
    },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map((it) => (
        <Card key={it.label}>
          <CardBody>
            <CardTitle>{it.label}</CardTitle>
            <div className="num mt-1.5 text-[26px] font-medium tracking-tightish text-zinc-50">
              {it.value}
            </div>
            <div className="mt-1 text-[11px] text-zinc-500 leading-[1.4]">{it.hint}</div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
