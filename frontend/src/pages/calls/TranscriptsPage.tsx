import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallListItem, Paginated } from "@/lib/types";
import { Card, PageHeader, Input } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState, Skeleton } from "@/components/ui/Bits";
import { CallDetailDrawer } from "@/components/CallDetailDrawer";
import { CALLS_SUBNAV } from "./CallHistoryPage";
import { formatDateTime, initials, titleCase } from "@/lib/format";
import { OutcomeBadge } from "@/components/StatusBadges";

// Transcripts live on each call (conversation_summaries). This is a searchable
// browser: pick a call to read its transcript + AI summary in the drawer.
export function TranscriptsPage() {
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["calls-transcripts", applied],
    queryFn: () =>
      api.get<Paginated<CallListItem>>("/calls", {
        query: { search: applied || undefined, limit: 30, offset: 0 },
      }),
  });

  return (
    <div>
      <PageHeader title="Transcripts" subtitle="Search and read AI conversation transcripts" />
      <SubNav items={CALLS_SUBNAV} />

      <form
        onSubmit={(e) => { e.preventDefault(); setApplied(search); }}
        className="relative mb-4"
      >
        <Icon name="search" className="pointer-events-none absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
        <Input className="!pl-10" placeholder="Search by lead name, phone or keyword…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </form>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
      ) : (data?.items.length ?? 0) === 0 ? (
        <EmptyState icon="transcript" title="No transcripts found" hint="Transcripts appear here after Priya completes calls." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data!.items.map((c) => (
            <Card key={c.id} hover className="cursor-pointer p-4" >
              <div onClick={() => setOpenId(c.id)}>
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">
                    {initials(c.lead_name || c.phone_number)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-slate-800">{c.lead_name || c.phone_number}</p>
                    <p className="text-xs text-slate-400">{titleCase(c.direction)} · {formatDateTime(c.call_date)}</p>
                  </div>
                  <OutcomeBadge outcome={c.outcome} />
                </div>
                <div className="mt-3 flex items-center gap-1 text-xs font-medium text-brand-600">
                  <Icon name="transcript" className="h-4 w-4" /> Read transcript
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CallDetailDrawer callId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
