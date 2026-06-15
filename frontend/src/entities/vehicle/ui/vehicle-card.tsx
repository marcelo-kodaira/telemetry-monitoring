import { batteryTone } from "@/entities/vehicle/lib/battery";
import type { Vehicle } from "@/entities/vehicle/model/vehicle.schema";
import { StatusBadge } from "@/entities/vehicle/ui/status-badge";
import { cn } from "@/shared/lib/cn";
import { Card } from "@/shared/ui/card";
import { ProgressBar } from "@/shared/ui/progress-bar";

export function VehicleCard({ v }: { v: Vehicle }) {
  return (
    <Card
      data-testid="vehicle-card"
      data-vehicle={v.vehicle_id}
      className={cn("space-y-2 p-3", v.is_offline && "opacity-50")}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm font-semibold">{v.vehicle_id}</span>
        <StatusBadge status={v.status} />
      </div>
      <ProgressBar className="h-2 w-full" value={v.battery_pct} fillClassName={batteryTone(v.battery_pct)} />
      <div className="text-xs text-slate-500">
        {v.battery_pct}%{v.is_offline ? " · offline" : ""}
      </div>
      {v.active_anomalies.length > 0 && (
        <div data-testid="vehicle-anomaly" className="truncate text-xs text-red-600">
          ⚠ {v.active_anomalies.join(", ")}
        </div>
      )}
    </Card>
  );
}
