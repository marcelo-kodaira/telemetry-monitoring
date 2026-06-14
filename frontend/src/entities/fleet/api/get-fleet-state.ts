import { fetchJson } from "@/shared/api/client";
import { fleetStateSchema } from "@/entities/fleet/model/fleet.schema";

export const getFleetState = () => fetchJson("/fleet/state", fleetStateSchema);
