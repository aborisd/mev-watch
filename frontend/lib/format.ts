export function shortAddr(a: string | null | undefined, pad = 4): string {
  if (!a) return "—";
  const s = a.toLowerCase();
  return s.length > 2 + pad * 2 ? `${s.slice(0, 2 + pad)}…${s.slice(-pad)}` : s;
}

export function fmtUsd(x: string | number | null | undefined, digits = 2): string {
  if (x === null || x === undefined) return "—";
  const n = typeof x === "string" ? Number(x) : x;
  if (!Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(2)}k`;
  return `$${n.toFixed(digits)}`;
}

export function fmtInt(x: number | null | undefined): string {
  if (x === null || x === undefined) return "—";
  return x.toLocaleString("en-US");
}

export function relTime(iso: string | Date): string {
  const t = typeof iso === "string" ? new Date(iso).getTime() : iso.getTime();
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  return `${d}d`;
}

export function etherscanTx(hash: string | null | undefined): string | null {
  if (!hash) return null;
  return `https://etherscan.io/tx/${hash}`;
}

export function etherscanAddr(addr: string | null | undefined): string | null {
  if (!addr) return null;
  return `https://etherscan.io/address/${addr}`;
}
