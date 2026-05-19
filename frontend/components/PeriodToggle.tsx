"use client";

import clsx from "clsx";
import type { Period } from "@/lib/types";

const PERIODS: Period[] = ["1h", "24h", "7d", "30d"];

export function PeriodToggle({
  value,
  onChange,
}: {
  value: Period;
  onChange: (p: Period) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-surface-raised p-0.5">
      {PERIODS.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={clsx(
            "num px-2.5 py-1 text-[12px] rounded-md transition-colors",
            p === value
              ? "bg-zinc-800 text-zinc-100"
              : "text-zinc-500 hover:text-zinc-300",
          )}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
