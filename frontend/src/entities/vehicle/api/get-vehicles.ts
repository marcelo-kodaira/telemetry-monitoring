import { fetchJson } from "@/shared/api/client";
import { vehiclesSchema } from "@/entities/vehicle/model/vehicle.schema";

export const getVehicles = () => fetchJson("/vehicles", vehiclesSchema);
