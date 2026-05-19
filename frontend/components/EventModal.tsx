"use client";

import { useEffect } from "react";

import { etherscanAddr, etherscanTx, fmtUsd, shortAddr } from "@/lib/format";
import type { MevEvent } from "@/lib/types";
import { Badge } from "./ui/Badge";
import { BlockBar, type BlockMarker } from "./BlockBar";

export function EventModal({
  event,
  onClose,
}: {
  event: MevEvent | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!event) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [event, onClose]);

  if (!event) return null;

  const md = (event.metadata ?? {}) as Record<string, number | string | boolean>;
  const isSandwich = event.type === "sandwich";
  const markers: BlockMarker[] = isSandwich
    ? [
        { idx: num(md.front_tx_index), label: "Front", variant: "front" },
        { idx: num(md.victim_tx_index), label: "Victim", variant: "victim" },
        { idx: num(md.back_tx_index), label: "Back", variant: "back" },
      ]
    : [
        { idx: num(md.mint_tx_index), label: "Mint", variant: "front" },
        { idx: num(md.victim_tx_index), label: "Victim", variant: "victim" },
        { idx: num(md.burn_tx_index), label: "Burn", variant: "back" },
      ];

  const typeExplainer = isSandwich
    ? "A bot bought this token right before the victim's swap to push the price up, then sold right after to capture the difference."
    : "A bot added liquidity to this pool seconds before the victim's swap, collected most of the fee, then pulled liquidity back out.";

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center px-4 pt-16 pb-8 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border border-line bg-surface-raised shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between px-5 py-4 border-b border-line">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant={event.type === "sandwich" ? "sandwich" : "jit"}>
                {event.type}
              </Badge>
              <span className="text-[11px] text-zinc-500 mono">
                block {event.block_number.toLocaleString()}
              </span>
              <span className="text-[11px] text-zinc-600">·</span>
              <span className="text-[11px] text-zinc-500">
                {new Date(event.block_ts).toLocaleString()}
              </span>
            </div>
            <div className="num text-[30px] tracking-tightish font-medium text-emerald-300">
              {fmtUsd(event.net_profit_usd)}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-200 transition-colors text-[18px] -mt-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          <section className="rounded-md border border-line bg-surface px-3 py-2.5 text-[12.5px] text-zinc-300 leading-[1.55]">
            {typeExplainer}
          </section>

          <section>
            <div className="text-[11px] uppercase tracking-[0.08em] text-zinc-500 mb-1">
              Position in block
            </div>
            <div className="text-[11px] text-zinc-500 mb-2">
              Where the three transactions sat inside the block. Tight clustering in the
              correct order is the sandwich signature.
            </div>
            <BlockBar markers={markers} />
          </section>

          <section className="grid grid-cols-2 gap-4">
            <KV
              label="Extractor EOA"
              caption="Wallet that profited"
              value={shortAddr(event.extractor_eoa)}
              href={etherscanAddr(event.extractor_eoa)}
            />
            <KV
              label="Bot contract"
              caption="Smart contract used by the bot"
              value={shortAddr(event.extractor_contract)}
              href={etherscanAddr(event.extractor_contract ?? undefined)}
            />
            <KV
              label="Victim EOA"
              caption="The trader who lost money"
              value={shortAddr(event.victim_eoa)}
              href={etherscanAddr(event.victim_eoa ?? undefined)}
            />
            <KV
              label="Pool"
              caption="Uniswap trading pair"
              value={shortAddr(event.pool)}
              href={etherscanAddr(event.pool)}
            />
          </section>

          <section>
            <div className="text-[11px] uppercase tracking-[0.08em] text-zinc-500 mb-1">
              Transactions
            </div>
            <div className="text-[11px] text-zinc-500 mb-2">
              {isSandwich
                ? "Front (bot buys) → Victim (unlucky swap) → Back (bot sells)."
                : "Mint (bot adds liquidity) → Victim (big swap pays fees) → Burn (bot removes liquidity)."}
            </div>
            <div className="space-y-1.5">
              <TxRow label={event.type === "sandwich" ? "Front" : "Mint"} hash={event.frontrun_tx} variant="front" />
              <TxRow label="Victim" hash={event.victim_tx} variant="victim" />
              <TxRow label={event.type === "sandwich" ? "Back" : "Burn"} hash={event.backrun_tx} variant="back" />
            </div>
          </section>

          {md.quote_unavailable === true && (
            <div className="text-[11px] text-zinc-500 bg-zinc-900/60 border border-line rounded-md px-3 py-2">
              Profit token unpriceable — USD figure may be unreliable.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function num(v: unknown): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

function KV({
  label,
  value,
  href,
  caption,
}: {
  label: string;
  value: string;
  href: string | null | undefined;
  caption?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.08em] text-zinc-500">{label}</div>
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="mono text-zinc-100 hover:text-emerald-300 text-[12.5px]"
        >
          {value}
        </a>
      ) : (
        <span className="mono text-zinc-500 text-[12.5px]">{value}</span>
      )}
      {caption && <div className="text-[10.5px] text-zinc-500 mt-0.5">{caption}</div>}
    </div>
  );
}

function TxRow({
  label,
  hash,
  variant,
}: {
  label: string;
  hash: string | null;
  variant: "front" | "victim" | "back";
}) {
  const accent = {
    front: "text-amber-300",
    victim: "text-zinc-100",
    back: "text-amber-300",
  }[variant];
  return (
    <div className="flex items-center justify-between px-3 py-2 rounded-md border border-line/80 bg-surface">
      <div className="flex items-center gap-2">
        <span className={`text-[11px] uppercase tracking-[0.08em] ${accent}`}>{label}</span>
      </div>
      {hash ? (
        <a
          href={etherscanTx(hash) ?? "#"}
          target="_blank"
          rel="noreferrer"
          className="mono text-[12px] text-zinc-300 hover:text-emerald-300"
        >
          {shortAddr(hash, 6)}
        </a>
      ) : (
        <span className="mono text-[12px] text-zinc-600">—</span>
      )}
    </div>
  );
}
