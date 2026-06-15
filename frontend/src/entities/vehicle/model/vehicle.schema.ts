import { z } from "zod";

export const latestAnomalySchema = z.object({
  type: z.string(),
  severity: z.enum(["critical", "warning"]),
  detected_at: z.string(),
});

export const vehicleStatusEnum = z.enum(["idle", "moving", "charging", "fault"]);
export type VehicleStatus = z.infer<typeof vehicleStatusEnum>;

export const vehicleSchema = z.object({
  vehicle_id: z.string(),
  status: vehicleStatusEnum,
  battery_pct: z.number(),
  lat: z.number().nullable(),
  lon: z.number().nullable(),
  is_offline: z.boolean(),
  last_seen_at: z.string().nullable(),
  latest_anomaly: latestAnomalySchema.nullable(),
});

export const vehiclesSchema = z.array(vehicleSchema);
export type Vehicle = z.infer<typeof vehicleSchema>;
