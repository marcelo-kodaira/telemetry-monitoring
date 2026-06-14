import { z } from "zod";

export const fleetStateSchema = z.object({
  generated_at: z.string(),
  total: z.number(),
  offline: z.number(),
  counts: z.object({
    idle: z.number(),
    moving: z.number(),
    charging: z.number(),
    fault: z.number(),
  }),
});

export type FleetState = z.infer<typeof fleetStateSchema>;
