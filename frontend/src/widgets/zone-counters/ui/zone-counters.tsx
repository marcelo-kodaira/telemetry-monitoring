import { getZoneCounts, zonesKey } from "@/entities/zone";
import { usePolledQuery } from "@/shared/lib/hooks/use-polled-query";
import { EmptyState } from "@/shared/ui/empty-state";
import { ProgressBar } from "@/shared/ui/progress-bar";
import { QueryBoundary } from "@/shared/ui/query-boundary";
import { Skeleton } from "@/shared/ui/skeleton";

const SKELETON_ROWS = 8;

function RowsSkeleton() {
  return (
    <div className="space-y-1">
      {Array.from({ length: SKELETON_ROWS }).map((_, i) => (
        <Skeleton key={i} className="h-4" />
      ))}
    </div>
  );
}

export function ZoneCounters() {
  const query = usePolledQuery(zonesKey, getZoneCounts);
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold">Zone entries</h2>
      <QueryBoundary
        query={query}
        loading={<RowsSkeleton />}
        isEmpty={(data) => data.zones.length === 0}
        empty={<EmptyState message="No zones configured." />}
        errorMessage="Couldn't load zone counts."
      >
        {(data) => {
          const max = Math.max(1, ...data.zones.map((zone) => zone.entry_count));
          return (
            <ul data-testid="zone-counters" className="space-y-1">
              {data.zones.map((zone) => (
                <li key={zone.zone_id} data-zone={zone.zone_id} className="flex items-center gap-2 text-sm">
                  <span className="w-36 truncate font-mono text-xs">{zone.zone_id}</span>
                  <ProgressBar
                    className="h-3 flex-1"
                    value={(zone.entry_count / max) * 100}
                    fillClassName="bg-indigo-500"
                  />
                  <span data-testid="zone-count" className="w-10 text-right tabular-nums">
                    {zone.entry_count}
                  </span>
                </li>
              ))}
            </ul>
          );
        }}
      </QueryBoundary>
    </section>
  );
}
