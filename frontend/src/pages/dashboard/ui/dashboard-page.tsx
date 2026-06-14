import { FleetGrid } from "@/widgets/fleet-grid/ui/fleet-grid";
import { FleetSummary } from "@/widgets/fleet-summary/ui/fleet-summary";
import { ZoneCounters } from "@/widgets/zone-counters/ui/zone-counters";

export function DashboardPage() {
  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Fleet Telemetry Monitoring</h1>
        <p className="text-sm text-slate-500">Live · polling every 1.5s</p>
      </header>
      <FleetSummary />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <FleetGrid />
        <ZoneCounters />
      </div>
    </main>
  );
}
