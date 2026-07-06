import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallListItem, CallOutcome, Paginated } from "@/lib/types";
import { Button, Card, Input, PageHeader, Select } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { Pagination } from "@/components/ui/Pagination";
import { OutcomeBadge, ScoreBadge } from "@/components/StatusBadges";
import { formatDateTime, formatDuration, titleCase } from "@/lib/format";

const OUTCOMES: CallOutcome[] = [
  "completed", "not_interested", "callback_requested",
  "transfer_requested", "no_answer", "failed", "voicemail",
];
const LIMIT = 25;

interface Filters {
  search: string;
  outcome: string;
  date_from: string;
  date_to: string;
  duration_min: string;
  duration_max: string;
}
const EMPTY: Filters = { search: "", outcome: "", date_from: "", date_to: "", duration_min: "", duration_max: "" };

export function CallsPage() {
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [offset, setOffset] = useState(0);

  const query = {
    search: filters.search || undefined,
    outcome: filters.outcome || undefined,
    date_from: filters.date_from ? new Date(filters.date_from).toISOString() : undefined,
    date_to: filters.date_to ? new Date(filters.date_to).toISOString() : undefined,
    duration_min: filters.duration_min || undefined,
    duration_max: filters.duration_max || undefined,
    limit: LIMIT,
    offset,
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["calls", query],
    queryFn: () => api.get<Paginated<CallListItem>>("/calls", { query }),
  });

  return (
    <div>
      <PageHeader title="Calls" subtitle={data ? `${data.total} total` : undefined} />

      <Card className="mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input label="Search" placeholder="Name / number / room" value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} />
          <Select label="Outcome" value={draft.outcome} onChange={(e) => setDraft({ ...draft, outcome: e.target.value })}>
            <option value="">All outcomes</option>
            {OUTCOMES.map((o) => <option key={o} value={o}>{titleCase(o)}</option>)}
          </Select>
          <Input label="From date" type="date" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} />
          <Input label="To date" type="date" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <Input label="Min sec" type="number" min={0} value={draft.duration_min} onChange={(e) => setDraft({ ...draft, duration_min: e.target.value })} />
            <Input label="Max sec" type="number" min={0} value={draft.duration_max} onChange={(e) => setDraft({ ...draft, duration_max: e.target.value })} />
          </div>
          <div className="flex items-end gap-2 lg:col-span-2">
            <Button onClick={() => { setOffset(0); setFilters(draft); }}>Apply</Button>
            <Button variant="secondary" onClick={() => { setDraft(EMPTY); setFilters(EMPTY); setOffset(0); }}>Clear</Button>
          </div>
        </div>
      </Card>

      <Card>
        {isLoading && <LoadingBlock />}
        {isError && <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div>}
        {data && data.items.length === 0 && <div className="p-6"><EmptyState title="No calls found" /></div>}
        {data && data.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Lead</th>
                    <th className="px-4 py-3">Phone</th>
                    <th className="px-4 py-3">Direction</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Duration</th>
                    <th className="px-4 py-3">Outcome</th>
                    <th className="px-4 py-3">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <Link to={`/calls/${c.id}`} className="font-medium text-brand-700 hover:underline">
                          {c.lead_name || "Unknown"}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{c.phone_number || "—"}</td>
                      <td className="px-4 py-3 text-slate-600">{titleCase(c.direction)}</td>
                      <td className="px-4 py-3 text-slate-500">{formatDateTime(c.call_date)}</td>
                      <td className="px-4 py-3 text-slate-600">{formatDuration(c.duration_seconds)}</td>
                      <td className="px-4 py-3"><OutcomeBadge outcome={c.outcome} /></td>
                      <td className="px-4 py-3"><ScoreBadge score={c.qualification_score} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>
    </div>
  );
}
