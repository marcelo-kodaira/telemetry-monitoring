import { ErrorBoundary } from "@/app/error-boundary";
import { QueryProvider } from "@/app/providers/query-provider";
import { DashboardPage } from "@/pages/dashboard/ui/dashboard-page";

export default function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <DashboardPage />
      </QueryProvider>
    </ErrorBoundary>
  );
}
