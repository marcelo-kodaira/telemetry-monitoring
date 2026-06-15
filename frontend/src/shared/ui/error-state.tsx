export function ErrorState({
  message = "Something went wrong.",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
    >
      <span>⚠ {message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded border border-red-300 px-3 py-1 text-xs font-medium hover:bg-red-100"
        >
          Retry
        </button>
      )}
    </div>
  );
}
