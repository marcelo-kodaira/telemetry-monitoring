import { getZoneCounts } from "@/entities/zone/api/get-zone-counts";
import { usePolledQuery } from "@/shared/lib/hooks/use-polled-query";

export function ZoneCounters() {
  const { data } = usePolledQuery(["zones"], getZoneCounts);
  const zones = data?.zones ?? [];
  const max = Math.max(1, ...zones.map((z) => z.entry_count));
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold">Zone entries</h2>
      <ul data-testid="zone-counters" className="space-y-1">
        {zones.map((z) => (
          <li key={z.zone_id} data-zone={z.zone_id} className="flex items-center gap-2 text-sm">
            <span className="w-36 truncate font-mono text-xs">{z.zone_id}</span>
            <div className="h-3 flex-1 rounded bg-slate-100">
              <div
                className="h-3 rounded bg-indigo-500"
                style={{ width: `${(z.entry_count / max) * 100}%` }}
              />
            </div>
            <span data-testid="zone-count" className="w-10 text-right tabular-nums">
              {z.entry_count}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
