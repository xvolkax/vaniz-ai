import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallListItem, Paginated } from "@/lib/types";
import { Card, PageHeader, Input } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState, Skeleton } from "@/components/ui/Bits";
import { OutcomeBadge } from "@/components/StatusBadges";
import { CALLS_SUBNAV } from "./CallHistoryPage";
import { formatDateTime, formatDuration, initials, titleCase } from "@/lib/format";

// Recordings are data-driven: any call with a recording_url gets an audio
// player. Recording capture is enabled server-side (RECORDING_ENABLED + egress).
export function RecordingsPage() {
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["calls-recordings", applied],
    queryFn: () =>
      api.get<Paginated<CallListItem>>("/calls", {
        query: { search: applied || undefined, limit: 50, offset: 0 },
      }),
  });

  const withRecording = (data?.items ?? []).filter((c) => !!c.recording_url);

  return (
    <div>
      <PageHeader title="Recordings" subtitle="Listen back to your AI conversations" />
      <SubNav items={CALLS_SUBNAV} />

      <form onSubmit={(e) => { e.preventDefault(); setApplied(search); }} className="relative mb-4">
        <Icon name="search" className="pointer-events-none absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
        <Input className="!pl-10" placeholder="Search by lead name or phone…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </form>

      {isLoading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-2xl" />)}</div>
      ) : withRecording.length === 0 ? (
        <div>
          <EmptyState
            icon="recording"
            title="No recordings yet"
            hint="Recordings appear here automatically once call recording is enabled on your workspace. Ask your admin to turn on RECORDING_ENABLED."
          />
          <div className="mt-4 flex items-start gap-3 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
            <Icon name="recording" className="mt-0.5 h-4 w-4 shrink-0" />
            <span>When enabled, every call is recorded via LiveKit egress and streamed here with a built-in player — no extra setup in the dashboard.</span>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {withRecording.map((c) => (
            <Card key={c.id} className="p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">
                  {initials(c.lead_name || c.phone_number)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-slate-800">{c.lead_name || c.phone_number}</p>
                  <p className="text-xs text-slate-400">{titleCase(c.direction)} · {formatDateTime(c.call_date)} · {formatDuration(c.duration_seconds)}</p>
                </div>
                <OutcomeBadge outcome={c.outcome} />
                <a href={c.recording_url!} download className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-brand-600" title="Download">
                  <Icon name="download" className="h-4 w-4" />
                </a>
              </div>
              <audio controls preload="none" src={c.recording_url!} className="mt-3 w-full" />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
