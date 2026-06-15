import { z } from "zod";

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
  active_anomalies: z.array(z.string()),
});

export const vehiclesSchema = z.array(vehicleSchema);
export type Vehicle = z.infer<typeof vehicleSchema>;
