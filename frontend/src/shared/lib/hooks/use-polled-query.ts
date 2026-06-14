import { type QueryKey, useQuery } from "@tanstack/react-query";
import { POLL_INTERVAL_MS } from "@/shared/config";

export function usePolledQuery<T>(key: QueryKey, fn: () => Promise<T>) {
  return useQuery({
    queryKey: key,
    queryFn: fn,
    refetchInterval: POLL_INTERVAL_MS,
    placeholderData: (prev) => prev,
  });
}
