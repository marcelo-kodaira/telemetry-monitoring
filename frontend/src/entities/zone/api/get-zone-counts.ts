import { fetchJson } from "@/shared/api/client";
import { zoneCountsSchema } from "@/entities/zone/model/zone.schema";

export const getZoneCounts = () => fetchJson("/zones/counts", zoneCountsSchema);
