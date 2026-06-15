import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ErrorState } from "@/shared/ui/error-state";

/**
 * Renders one of four states for a query: error (only when there is no data to fall back on),
 * loading skeleton, empty, or content. With `placeholderData` keeping the last value, a failed
 * background refetch keeps showing stale data here while the global toast reports the outage.
 */
export function QueryBoundary<T>({
  query,
  loading,
  empty,
  isEmpty,
  errorMessage,
  children,
}: {
  query: UseQueryResult<T>;
  loading: ReactNode;
  empty?: ReactNode;
  isEmpty?: (data: T) => boolean;
  errorMessage?: string;
  children: (data: T) => ReactNode;
}) {
  if (query.data === undefined) {
    if (query.isError) return <ErrorState message={errorMessage} onRetry={() => query.refetch()} />;
    return <>{loading}</>;
  }
  if (empty && isEmpty?.(query.data)) return <>{empty}</>;
  return <>{children(query.data)}</>;
}
