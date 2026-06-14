import { batteryTone, statusTone } from "@/entities/vehicle/lib/battery";
import type { Vehicle } from "@/entities/vehicle/model/vehicle.schema";
import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

export function VehicleCard({ v }: { v: Vehicle }) {
  return (
    <Card
      data-testid="vehicle-card"
      data-vehicle={v.vehicle_id}
      className={`space-y-2 p-3 ${v.is_offline ? "opacity-50" : ""}`}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm font-semibold">{v.vehicle_id}</span>
        <Badge className={statusTone(v.status)}>{v.status}</Badge>
      </div>
      <div className="h-2 w-full rounded bg-slate-100">
        <div className={`h-2 rounded ${batteryTone(v.battery_pct)}`} style={{ width: `${v.battery_pct}%` }} />
      </div>
      <div className="text-xs text-slate-500">
        {v.battery_pct}%{v.is_offline ? " · offline" : ""}
      </div>
      {v.latest_anomaly && (
        <div data-testid="vehicle-anomaly" className="truncate text-xs text-red-600">
          ⚠ {v.latest_anomaly.type} ({v.latest_anomaly.severity})
        </div>
      )}
    </Card>
  );
}
