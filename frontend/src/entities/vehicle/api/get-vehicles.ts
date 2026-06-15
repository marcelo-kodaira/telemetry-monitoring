import { fetchJson } from "@/shared/api/client";
import { vehiclesSchema } from "@/entities/vehicle/model/vehicle.schema";

export const vehiclesKey = ["vehicles"] as const;
export const getVehicles = () => fetchJson("/vehicles", vehiclesSchema);
