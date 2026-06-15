import { cva } from "class-variance-authority";
import type { VehicleStatus } from "@/entities/vehicle/model/vehicle.schema";
import { Badge } from "@/shared/ui/badge";

// Exhaustively keyed by VehicleStatus — a new status is a compile error until coloured here.
const statusColors = cva("", {
  variants: {
    status: {
      idle: "bg-slate-200 text-slate-700",
      moving: "bg-blue-100 text-blue-700",
      charging: "bg-emerald-100 text-emerald-700",
      fault: "bg-red-100 text-red-700",
    } satisfies Record<VehicleStatus, string>,
  },
});

export function StatusBadge({ status }: { status: VehicleStatus }) {
  return <Badge className={statusColors({ status })}>{status}</Badge>;
}
