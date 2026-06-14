import { getFleetState } from "@/entities/fleet/api/get-fleet-state";
import { usePolledQuery } from "@/shared/lib/hooks/use-polled-query";

export function FleetSummary() {
  const { data } = usePolledQuery(["fleet"], getFleetState);
  if (!data) return null;
  const items = [
    ["idle", data.counts.idle],
    ["moving", data.counts.moving],
    ["charging", data.counts.charging],
    ["fault", data.counts.fault],
    ["offline", data.offline],
  ] as const;
  return (
    <section data-testid="fleet-summary" className="flex flex-wrap gap-3">
      {items.map(([label, n]) => (
        <div key={label} className="rounded-lg border border-slate-200 bg-white px-4 py-2 shadow-sm">
          <div className="text-2xl font-bold tabular-nums" data-testid={`count-${label}`}>
            {n}
          </div>
          <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
        </div>
      ))}
    </section>
  );
}
