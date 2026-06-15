import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Toaster, toast } from "sonner";

const CONNECTION_TOAST_ID = "api-connection";

// Single source of connection status across all polled queries: a persistent error toast when any
// fetch fails, dismissed/replaced by a brief "reconnected" toast on the next success.
let isDisconnected = false;
const queryCache = new QueryCache({
  onError: () => {
    isDisconnected = true;
    toast.error("Lost connection to the telemetry API — retrying…", {
      id: CONNECTION_TOAST_ID,
      duration: Infinity,
    });
  },
  onSuccess: () => {
    if (isDisconnected) {
      isDisconnected = false;
      toast.success("Reconnected to the telemetry API", { id: CONNECTION_TOAST_ID, duration: 2500 });
    }
  },
});

const client = new QueryClient({
  queryCache,
  defaultOptions: { queries: { staleTime: 0, retry: 1 } },
});

export function QueryProvider({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      {children}
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  );
}
