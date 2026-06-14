import { QueryProvider } from "@/app/providers/query-provider";
import { DashboardPage } from "@/pages/dashboard/ui/dashboard-page";

export default function App() {
  return (
    <QueryProvider>
      <DashboardPage />
    </QueryProvider>
  );
}
