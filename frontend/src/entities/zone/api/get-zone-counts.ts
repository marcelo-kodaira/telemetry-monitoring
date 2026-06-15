import { fetchJson } from "@/shared/api/client";
import { zoneCountsSchema } from "@/entities/zone/model/zone.schema";

export const zonesKey = ["zones"] as const;
export const getZoneCounts = () => fetchJson("/zones/counts", zoneCountsSchema);
