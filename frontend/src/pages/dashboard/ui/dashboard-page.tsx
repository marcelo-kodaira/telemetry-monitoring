import { POLL_INTERVAL_MS } from "@/shared/config";
import { FleetGrid } from "@/widgets/fleet-grid";
import { FleetSummary } from "@/widgets/fleet-summary";
import { ZoneCounters } from "@/widgets/zone-counters";

export function DashboardPage() {
  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Fleet Telemetry Monitoring</h1>
        <p className="text-sm text-slate-500">Live · polling every {POLL_INTERVAL_MS / 1000}s</p>
      </header>
      <FleetSummary />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <FleetGrid />
        <ZoneCounters />
      </div>
    </main>
  );
}
