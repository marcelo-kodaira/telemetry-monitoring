import { expect, test } from "@playwright/test";

const API = process.env.VITE_API_URL ?? "http://localhost:8000";

function telemetry(vehicle_id: string, zone: string | null) {
  return {
    vehicle_id,
    ts: new Date().toISOString(),
    lat: 37.41,
    lon: -122.08,
    battery_pct: 80,
    speed_mps: 1.0,
    status: "moving",
    error_codes: [],
    zone_entered: zone,
  };
}

test("renders the 50-vehicle fleet grid with summary and zone panels", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("vehicle-card")).toHaveCount(50, { timeout: 10_000 });
  await expect(page.getByTestId("fleet-summary")).toBeVisible();
  await expect(page.getByTestId("zone-counters")).toBeVisible();
});

test("zone count updates live after a zone entry", async ({ page, request }) => {
  // maintenance_bay is never touched by the simulator, so the +1 is deterministic
  await page.goto("/");
  const cell = page.locator('[data-zone="maintenance_bay"] [data-testid="zone-count"]');
  await expect(cell).toBeVisible();
  const before = Number(await cell.textContent());
  await request.post(`${API}/telemetry`, { data: telemetry("v-1", "maintenance_bay") });
  await expect(cell).toHaveText(String(before + 1), { timeout: 6_000 });
});

test("a faulted vehicle surfaces a fault state in its card", async ({ page, request }) => {
  await request.post(`${API}/vehicles/v-5/status`, { data: { status: "fault", reason: "e2e" } });
  await page.goto("/");
  await expect(page.locator('[data-vehicle="v-5"]')).toContainText("fault", { timeout: 6_000 });
});

test("shows a dedicated error state and a connection toast when the API is unreachable", async ({ page }) => {
  for (const path of ["**/vehicles", "**/fleet/state", "**/zones/counts"]) {
    await page.route(path, (route) => route.abort());
  }
  await page.goto("/");
  await expect(page.getByText("Couldn't load the fleet.")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Lost connection to the telemetry API/i)).toBeVisible({ timeout: 10_000 });
});
