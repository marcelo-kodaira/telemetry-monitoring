import { BATTERY_CRITICAL_PCT, BATTERY_LOW_PCT } from "@/shared/config";

export function batteryTone(pct: number): string {
  if (pct <= BATTERY_CRITICAL_PCT) return "bg-red-500";
  if (pct <= BATTERY_LOW_PCT) return "bg-amber-500";
  return "bg-emerald-500";
}
