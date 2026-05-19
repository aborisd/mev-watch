import clsx from "clsx";
import type { HTMLAttributes } from "react";

type Variant = "sandwich" | "jit" | "muted" | "profit" | "danger";

export function Badge({
  variant = "muted",
  className,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  const map: Record<Variant, string> = {
    sandwich: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
    jit: "bg-violet-400/10 text-violet-300 ring-violet-400/20",
    muted: "bg-zinc-800/60 text-zinc-400 ring-zinc-700/40",
    profit: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
    danger: "bg-red-400/10 text-red-300 ring-red-400/20",
  };
  return (
    <span
      {...rest}
      className={clsx(
        "inline-flex items-center rounded-md px-1.5 py-0.5 text-[10.5px] font-medium ring-1 ring-inset uppercase tracking-[0.06em]",
        map[variant],
        className,
      )}
    />
  );
}
