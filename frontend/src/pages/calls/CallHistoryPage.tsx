import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallListItem, CallOutcome, Paginated } from "@/lib/types";
import { Card, PageHeader, Input, Select, Button } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { Skeleton, SubNav, EmptyState } from "@/components/ui/Bits";
import { Pagination } from "@/components/ui/Pagination";
import { ErrorState } from "@/components/ui/States";
import { OutcomeBadge, ScorePill } from "@/components/StatusBadges";
import { CallDetailDrawer } from "@/components/CallDetailDrawer";
import { formatDateTime, formatDuration, titleCase, initials } from "@/lib/format";

const OUTCOMES: CallOutcome[] = [
  "completed", "not_interested", "callback_requested",
  "transfer_requested", "no_answer", "failed", "voicemail",
];
const LIMIT = 25;

export const CALLS_SUBNAV = [
  { to: "/calls/live", label: "Live Calls" },
  { to: "/calls/history", label: "Call History" },
  { to: "/calls/recordings", label: "Recordings" },
  { to: "/calls/transcripts", label: "Transcripts" },
];

export function CallHistoryPage() {
  const [draft, setDraft] = useState({ search: "", outcome: "", date_from: "", date_to: "" });
  const [filters, setFilters] = useState(draft);
  const [offset, setOffset] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);

  const query = {
    search: filters.search || undefined,
    outcome: filters.outcome || undefined,
    date_from: filters.date_from ? new Date(filters.date_from).toISOString() : undefined,
    date_to: filters.date_to ? new Date(filters.date_to).toISOString() : undefined,
    limit: LIMIT,
    offset,
  };
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["calls", query],
    queryFn: () => api.get<Paginated<CallListItem>>("/calls", { query }),
  });

  return (
    <div>
      <PageHeader title="Calls" subtitle="Every conversation Priya has had with your leads" />
      <SubNav items={CALLS_SUBNAV} />

      <Card className="mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Input label="Search" placeholder="Lead, number or room" value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} />
          </div>
          <Select label="Outcome" value={draft.outcome} onChange={(e) => setDraft({ ...draft, outcome: e.target.value })}>
            <option value="">All outcomes</option>
            {OUTCOMES.map((o) => <option key={o} value={o}>{titleCase(o)}</option>)}
          </Select>
          <Input label="From" type="date" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} />
          <div className="flex items-end gap-2">
            <Input label="To" type="date" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} />
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={() => { setOffset(0); setFilters(draft); }}>Apply filters</Button>
          <Button size="sm" variant="ghost" onClick={() => { const e = { search: "", outcome: "", date_from: "", date_to: "" }; setDraft(e); setFilters(e); setOffset(0); }}>Clear</Button>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {isLoading && <div className="space-y-2 p-4">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>}
        {isError && <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div>}
        {data && data.items.length === 0 && <div className="p-6"><EmptyState icon="phone" title="No calls found" hint="Adjust filters, or launch a campaign to start calling." /></div>}
        {data && data.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-5 py-3">Lead</th>
                    <th className="px-5 py-3">Direction</th>
                    <th className="px-5 py-3">Outcome</th>
                    <th className="px-5 py-3">Duration</th>
                    <th className="px-5 py-3">Score</th>
                    <th className="px-5 py-3">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((c) => (
                    <tr key={c.id} onClick={() => setOpenId(c.id)} className="cursor-pointer transition hover:bg-brand-50/40">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">
                            {initials(c.lead_name || c.phone_number)}
                          </span>
                          <div>
                            <p className="font-semibold text-slate-800">{c.lead_name || "Unknown"}</p>
                            <p className="text-xs text-slate-400">{c.phone_number || "—"}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <span className="inline-flex items-center gap-1.5 text-slate-600">
                          <Icon name={c.direction === "outbound" ? "phone-outgoing" : "phone-incoming"} className="h-4 w-4 text-slate-400" />
                          {titleCase(c.direction)}
                        </span>
                      </td>
                      <td className="px-5 py-3"><OutcomeBadge outcome={c.outcome} /></td>
                      <td className="px-5 py-3 text-slate-600">{formatDuration(c.duration_seconds)}</td>
                      <td className="px-5 py-3"><ScorePill score={c.qualification_score} /></td>
                      <td className="px-5 py-3 text-slate-400">{formatDateTime(c.call_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>

      <CallDetailDrawer callId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
