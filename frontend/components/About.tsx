"use client";

import { useEffect } from "react";

export function About({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);

  if (!open) return null;

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
          <div>
            <div className="text-[11px] uppercase tracking-[0.08em] text-zinc-500">About</div>
            <div className="mt-1 text-[18px] font-medium tracking-tightish text-zinc-50">
              How this dashboard works
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-200 text-[18px] -mt-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 space-y-5 text-[13px] text-zinc-300 leading-[1.55]">
          <section>
            <h3 className="text-[11px] uppercase tracking-[0.08em] text-zinc-500 mb-1.5">
              The short version
            </h3>
            <p>
              When you swap tokens on a decentralised exchange, your transaction sits in a
              public queue for a few seconds before it's included in a block. Bots read that
              queue and sneak their own trades around yours to profit at your expense. Every
              row on this dashboard is money a bot took from an ordinary trader in real time.
            </p>
          </section>

          <Term
            title="Sandwich attack"
            body={
              <>
                A bot sees your pending swap, buys the same token <em>right before you</em>{" "}
                (pushing the price up), lets your swap execute at a worse price, then sells{" "}
                <em>right after you</em> — pocketing the difference. Three transactions in the
                same block: bot-buy, your-swap, bot-sell.
              </>
            }
          />

          <Term
            title="JIT (Just-In-Time) liquidity"
            body={
              <>
                A bot temporarily adds liquidity to a trading pool microseconds before a big
                swap, collects most of the swap fee, then immediately removes the liquidity —
                earning fees without taking any real risk. Only exists on Uniswap V3.
              </>
            }
          />

          <Term
            title="Extractor / Bot"
            body={
              <>
                The wallet (EOA) that profited. In practice it controls a deployed smart
                contract which does the actual bundling. Same extractor usually attacks many
                victims with the same recipe.
              </>
            }
          />

          <Term
            title="Victim"
            body={
              <>
                A regular trader whose swap got front-run. They paid more (or received less)
                than they would have without the bot. They usually don't even know they were
                sandwiched.
              </>
            }
          />

          <Term
            title="Pool"
            body={
              <>
                A Uniswap trading pair — for example WETH / USDC. Each pool is its own
                on-chain contract. Pools with thin liquidity get sandwiched more because the
                price moves a lot on every swap.
              </>
            }
          />

          <Term
            title="Net profit (USD)"
            body={
              <>
                Gross profit <em>minus</em> gas paid for the attack's transactions.{" "}
                <span className="text-zinc-500">
                  Note: bribes the bot paid directly to block builders (common via Flashbots)
                  are not yet subtracted — real net profit can be lower. Listed as a known
                  limitation.
                </span>
              </>
            }
          />

          <Term
            title="Position in block"
            body={
              <>
                Click any event to see a small bar visualising where the three transactions
                sat inside the block. For a sandwich, the pattern is always{" "}
                <span className="text-amber-300">front</span> →{" "}
                <span className="text-zinc-100">victim</span> →{" "}
                <span className="text-amber-300">back</span> — tightly clustered, in that
                order.
              </>
            }
          />

          <div className="rounded-md border border-line bg-surface px-3 py-2 text-[12px] text-zinc-400">
            <span className="text-zinc-200">Data source:</span> live Ethereum mainnet via
            Chainstack · Uniswap V2 &amp; V3 only · ingested within ~15&nbsp;s of each block.
          </div>

          <section className="pt-1 flex items-center justify-between text-[12px]">
            <span className="text-zinc-500">Built by</span>
            <div className="flex items-center gap-3">
              <a
                href="https://instagram.com/aborisd"
                target="_blank"
                rel="noreferrer"
                className="text-zinc-200 hover:text-emerald-300"
              >
                instagram · @aborisd
              </a>
              <a
                href="https://github.com/aborisd"
                target="_blank"
                rel="noreferrer"
                className="text-zinc-200 hover:text-emerald-300"
              >
                github · @aborisd
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function Term({ title, body }: { title: string; body: React.ReactNode }) {
  return (
    <section>
      <h3 className="text-zinc-100 font-medium">{title}</h3>
      <p className="mt-0.5 text-zinc-400">{body}</p>
    </section>
  );
}
