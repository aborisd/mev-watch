import clsx from "clsx";
import type { HTMLAttributes } from "react";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={clsx(
        "rounded-xl border border-line bg-surface-raised",
        "shadow-[0_1px_0_0_rgba(255,255,255,0.02)_inset]",
        className,
      )}
    />
  );
}

export function CardHeader({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={clsx(
        "flex items-center justify-between px-4 py-3 border-b border-line",
        className,
      )}
    />
  );
}

export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={clsx(
        "text-[12px] uppercase tracking-[0.08em] text-zinc-500 font-medium",
        className,
      )}
    />
  );
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div {...rest} className={clsx("p-4", className)} />;
}
