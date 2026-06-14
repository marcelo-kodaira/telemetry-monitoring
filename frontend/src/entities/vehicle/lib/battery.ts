export function batteryTone(pct: number): string {
  if (pct <= 5) return "bg-red-500";
  if (pct <= 15) return "bg-amber-500";
  return "bg-emerald-500";
}

export function statusTone(status: string): string {
  const tones: Record<string, string> = {
    idle: "bg-slate-200 text-slate-700",
    moving: "bg-blue-100 text-blue-700",
    charging: "bg-emerald-100 text-emerald-700",
    fault: "bg-red-100 text-red-700",
  };
  return tones[status] ?? "bg-slate-100 text-slate-700";
}
