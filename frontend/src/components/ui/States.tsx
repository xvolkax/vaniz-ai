import { Icon } from "./Icon";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className="flex flex-col items-center rounded-2xl border border-rose-200 bg-rose-50/60 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-rose-100 text-rose-600">
        <Icon name="x" className="h-6 w-6" />
      </div>
      <p className="mt-4 font-semibold text-rose-800">Unable to load data</p>
      <p className="mt-1 max-w-md text-sm text-rose-600">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700"
        >
          Try again
        </button>
      )}
    </div>
  );
}
