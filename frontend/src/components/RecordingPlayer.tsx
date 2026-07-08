import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { RecordingUrl } from "@/lib/types";
import { Icon } from "@/components/ui/Icon";

// Secure recording playback. The storage bucket is PRIVATE — we never receive a
// raw object URL. Instead we ask the API for a short-lived presigned URL and use
// it for the <audio> element and the download link. When it expires, the audio
// element errors and we transparently refetch a fresh URL.
//
// States handled: no recording, still processing (404), access denied (403),
// storage misconfigured (503), network errors, and URL expiry.
export function RecordingPlayer({
  callId,
  available,
  compact = false,
}: {
  callId: string;
  available: boolean;
  compact?: boolean;
}) {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["recording", callId],
    queryFn: () => api.get<RecordingUrl>(`/calls/${callId}/recording`),
    enabled: available,
    // Refetch a little before the presigned URL expires (TTL is ~10 min).
    staleTime: 8 * 60 * 1000,
    gcTime: 8 * 60 * 1000,
    retry: false,
  });

  if (!available) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white/60 p-4">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
          <Icon name="recording" className="h-5 w-5" />
        </span>
        <div className="text-sm">
          <p className="font-medium text-slate-700">No recording</p>
          <p className="text-xs text-slate-400">
            This call has no recording. Enable recording on your workspace to capture call audio.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return <div className="h-12 w-full animate-pulse rounded-xl bg-slate-100" />;
  }

  if (isError || !data) {
    const status = error instanceof ApiError ? error.status : 0;
    const msg =
      status === 404
        ? "Recording is still processing. Try again in a moment."
        : status === 403
        ? "You don't have permission to access this recording."
        : status === 503
        ? "Recording storage is not configured."
        : "Couldn't load the recording.";
    return (
      <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white/60 p-3 text-sm">
        <span className="text-slate-500">{msg}</span>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-lg px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={compact ? "" : "space-y-2"}>
      <div className="flex items-center gap-2">
        <audio
          controls
          preload="none"
          src={data.url}
          className="w-full"
          // On expiry (403 from storage) the element errors — fetch a fresh URL.
          onError={() => refetch()}
        />
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-brand-600"
          title="Download / open recording"
        >
          <Icon name="download" className="h-4 w-4" />
        </a>
      </div>
      {isFetching && <p className="text-[10px] text-slate-400">Refreshing secure link…</p>}
    </div>
  );
}
