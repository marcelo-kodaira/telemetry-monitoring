import { z } from "zod";
import { API_URL } from "@/shared/config";

export async function fetchJson<S extends z.ZodType>(path: string, schema: S): Promise<z.infer<S>> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return schema.parse(await res.json());
}
