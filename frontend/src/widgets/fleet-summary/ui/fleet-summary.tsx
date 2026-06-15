import { fleetKey, getFleetState } from "@/entities/fleet";
import { usePolledQuery } from "@/shared/lib/hooks/use-polled-query";
import { QueryBoundary } from "@/shared/ui/query-boundary";
import { Skeleton } from "@/shared/ui/skeleton";

const SKELETON_TILES = 5;

function SummarySkeleton() {
  return (
    <div className="flex flex-wrap gap-3">
      {Array.from({ length: SKELETON_TILES }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-24" />
      ))}
    </div>
  );
}

export function FleetSummary() {
  const query = usePolledQuery(fleetKey, getFleetState);
  return (
    <QueryBoundary query={query} loading={<SummarySkeleton />} errorMessage="Couldn't load fleet state.">
      {(data) => {
        const tiles = [
          ["idle", data.counts.idle],
          ["moving", data.counts.moving],
          ["charging", data.counts.charging],
          ["fault", data.counts.fault],
          ["offline", data.offline],
        ] as const;
        return (
          <section data-testid="fleet-summary" className="flex flex-wrap gap-3">
            {tiles.map(([label, count]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white px-4 py-2 shadow-sm">
                <div className="text-2xl font-bold tabular-nums" data-testid={`count-${label}`}>
                  {count}
                </div>
                <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
              </div>
            ))}
          </section>
        );
      }}
    </QueryBoundary>
  );
}
