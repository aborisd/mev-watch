"use client";

import clsx from "clsx";

export interface BlockMarker {
  idx: number;
  label: string;
  variant: "front" | "victim" | "back";
}

/**
 * Horizontal bar representing a block's transactions. Three markers are placed
 * along it at their tx_index positions.
 *
 * The underlying bar length is an assumption — most Ethereum blocks have ~150-200
 * txs — but the relative ordering and clustering of the three markers is what
 * conveys the attack pattern.
 */
export function BlockBar({
  markers,
  estimatedLength = 200,
}: {
  markers: BlockMarker[];
  estimatedLength?: number;
}) {
  const maxIdx = Math.max(estimatedLength, ...markers.map((m) => m.idx + 5));

  const colors: Record<BlockMarker["variant"], string> = {
    front: "bg-amber-400",
    victim: "bg-zinc-100",
    back: "bg-amber-400",
  };

  return (
    <div className="space-y-2">
      <div className="relative h-1.5 rounded-full bg-zinc-800/70 overflow-visible">
        {markers.map((m) => {
          const pct = (m.idx / maxIdx) * 100;
          return (
            <div
              key={m.label + m.idx}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
              style={{ left: `${pct}%` }}
            >
              <div className={clsx("h-3 w-1 rounded-sm", colors[m.variant])} />
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3 text-[11px] text-zinc-500">
        {markers.map((m) => (
          <div key={m.label + m.idx} className="flex items-center gap-1.5">
            <span className={clsx("h-2 w-2 rounded-sm", colors[m.variant])} />
            <span>
              <span className="text-zinc-300">{m.label}</span>{" "}
              <span className="mono">#{m.idx}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
