"use client";

import { Card, CardBody, CardHeader, CardTitle } from "./ui/Card";
import { etherscanAddr, fmtUsd, shortAddr } from "@/lib/format";
import type { LeaderboardEntry } from "@/lib/types";

export function Leaderboard({
  entries,
  by,
  onByChange,
}: {
  entries: LeaderboardEntry[];
  by: "profit" | "count";
  onByChange: (b: "profit" | "count") => void;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div>
          <CardTitle>Top extractors</CardTitle>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            Wallets that profited the most — click to view on Etherscan
          </div>
        </div>
        <div className="inline-flex text-[11px] rounded-md border border-line bg-surface p-0.5">
          {(["profit", "count"] as const).map((k) => (
            <button
              key={k}
              onClick={() => onByChange(k)}
              className={
                "px-2 py-0.5 rounded-[5px] " +
                (by === k
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300")
              }
            >
              by {k}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardBody className="p-0">
        <div className="max-h-[560px] overflow-y-auto">
          <table className="w-full text-[12.5px]">
            <thead className="sticky top-0 bg-surface-raised z-10">
              <tr className="text-zinc-500 text-[11px] uppercase tracking-[0.06em]">
                <th className="text-left font-medium px-4 py-2 w-8">#</th>
                <th className="text-left font-medium px-2 py-2">Address</th>
                <th className="text-right font-medium px-2 py-2">Attacks</th>
                <th className="text-right font-medium px-4 py-2">Profit</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-zinc-500 py-10 text-[12px]">
                    No extractors yet — waiting for data.
                  </td>
                </tr>
              )}
              {entries.map((e, i) => (
                <tr
                  key={e.address}
                  className="border-t border-line/60 hover:bg-white/[0.015]"
                >
                  <td className="num text-zinc-500 px-4 py-2">{i + 1}</td>
                  <td className="mono px-2 py-2">
                    <a
                      href={etherscanAddr(e.address) ?? "#"}
                      target="_blank"
                      rel="noreferrer"
                      className="text-zinc-100 hover:text-emerald-300"
                    >
                      {shortAddr(e.address)}
                    </a>
                  </td>
                  <td className="num text-right text-zinc-300 px-2 py-2">{e.attack_count}</td>
                  <td className="num text-right text-emerald-300 px-4 py-2">
                    {fmtUsd(e.total_profit_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}
