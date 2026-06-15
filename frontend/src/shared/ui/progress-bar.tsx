import { cn } from "@/shared/lib/cn";

/** A horizontal track with a coloured fill. `value` is a 0-100 percentage. */
export function ProgressBar({
  value,
  fillClassName,
  className,
}: {
  value: number;
  fillClassName?: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded bg-slate-100", className)}>
      <div
        className={cn("h-full rounded", fillClassName)}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}
