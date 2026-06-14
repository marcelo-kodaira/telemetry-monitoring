export function vehicleNumber(id: string): number {
  return Number(id.replace(/^v-/, "")) || 0;
}
