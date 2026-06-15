import { VehicleCard, getVehicles, vehiclesKey } from "@/entities/vehicle";
import { usePolledQuery } from "@/shared/lib/hooks/use-polled-query";
import { vehicleNumber } from "@/shared/lib/format";
import { EmptyState } from "@/shared/ui/empty-state";
import { QueryBoundary } from "@/shared/ui/query-boundary";
import { Skeleton } from "@/shared/ui/skeleton";

const GRID = "grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5";
const SKELETON_CARDS = 10;

function GridSkeleton() {
  return (
    <div className={GRID}>
      {Array.from({ length: SKELETON_CARDS }).map((_, i) => (
        <Skeleton key={i} className="h-24" />
      ))}
    </div>
  );
}

export function FleetGrid() {
  const query = usePolledQuery(vehiclesKey, getVehicles);
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold">Fleet{query.data ? ` (${query.data.length})` : ""}</h2>
      <QueryBoundary
        query={query}
        loading={<GridSkeleton />}
        isEmpty={(vehicles) => vehicles.length === 0}
        empty={<EmptyState message="No vehicles are reporting telemetry." />}
        errorMessage="Couldn't load the fleet."
      >
        {(vehicles) => (
          <div data-testid="fleet-grid" className={GRID}>
            {[...vehicles]
              .sort((a, b) => vehicleNumber(a.vehicle_id) - vehicleNumber(b.vehicle_id))
              .map((v) => (
                <VehicleCard key={v.vehicle_id} v={v} />
              ))}
          </div>
        )}
      </QueryBoundary>
    </section>
  );
}
