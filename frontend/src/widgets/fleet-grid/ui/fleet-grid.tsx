import { getVehicles } from "@/entities/vehicle/api/get-vehicles";
import { VehicleCard } from "@/entities/vehicle/ui/vehicle-card";
import { usePolledQuery } from "@/shared/lib/hooks/use-polled-query";
import { vehicleNumber } from "@/shared/lib/format";

export function FleetGrid() {
  const { data, isError } = usePolledQuery(["vehicles"], getVehicles);
  if (isError) return <p className="text-red-600">Failed to load vehicles.</p>;
  const vehicles = [...(data ?? [])].sort(
    (a, b) => vehicleNumber(a.vehicle_id) - vehicleNumber(b.vehicle_id),
  );
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold">Fleet ({vehicles.length})</h2>
      <div
        data-testid="fleet-grid"
        className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5"
      >
        {vehicles.map((v) => (
          <VehicleCard key={v.vehicle_id} v={v} />
        ))}
      </div>
    </section>
  );
}
