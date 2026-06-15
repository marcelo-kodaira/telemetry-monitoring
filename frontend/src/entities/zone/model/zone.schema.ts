import { z } from "zod";

export const zoneCountsSchema = z.object({
  generated_at: z.string(),
  zones: z.array(z.object({ zone_id: z.string(), entry_count: z.number() })),
});

export type ZoneCounts = z.infer<typeof zoneCountsSchema>;
