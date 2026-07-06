import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Lead,
  LeadImportResult,
  LeadSource,
  LeadStatus,
  Paginated,
} from "@/lib/types";
import { Button, Card, Input, PageHeader, Select } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { Pagination } from "@/components/ui/Pagination";
import { LeadStatusBadge, ScoreBadge } from "@/components/StatusBadges";
import { formatDate, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const STATUSES: LeadStatus[] = ["new", "qualifying", "qualified", "unqualified", "booked", "lost"];
const SOURCES: LeadSource[] = ["inbound_call", "outbound_call", "manual", "csv_import", "api", "other"];
const LIMIT = 25;

interface Filters {
  search: string;
  status: string;
  source: string;
  score_min: string;
  score_max: string;
  date_from: string;
  date_to: string;
}

const EMPTY: Filters = {
  search: "",
  status: "",
  source: "",
  score_min: "",
  score_max: "",
  date_from: "",
  date_to: "",
};

export function LeadsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [offset, setOffset] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const query = {
    search: filters.search || undefined,
    status: filters.status || undefined,
    source: filters.source || undefined,
    score_min: filters.score_min || undefined,
    score_max: filters.score_max || undefined,
    date_from: filters.date_from ? new Date(filters.date_from).toISOString() : undefined,
    date_to: filters.date_to ? new Date(filters.date_to).toISOString() : undefined,
    limit: LIMIT,
    offset,
  };

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["leads", query],
    queryFn: () => api.get<Paginated<Lead>>("/leads", { query }),
  });

  const importMut = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<LeadImportResult>("/leads/import", form);
    },
    onSuccess: (res) => {
      alert(`Imported: ${res.created} created, ${res.updated} updated, ${res.skipped} skipped.`);
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e) => alert(e instanceof Error ? e.message : "Import failed"),
  });

  function applyFilters() {
    setOffset(0);
    setFilters(draft);
  }
  function clearFilters() {
    setDraft(EMPTY);
    setFilters(EMPTY);
    setOffset(0);
  }

  function exportCsv() {
    void api.download("/leads/export", "leads.csv", {
      query: {
        search: query.search,
        status: query.status,
        source: query.source,
        score_min: query.score_min,
        score_max: query.score_max,
        date_from: query.date_from,
        date_to: query.date_to,
      },
    });
  }

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle={data ? `${data.total} total` : undefined}
        actions={
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) importMut.mutate(f);
                e.target.value = "";
              }}
            />
            {hasRole("agent") && (
              <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={importMut.isPending}>
                Import CSV
              </Button>
            )}
            <Button variant="secondary" onClick={exportCsv}>Export CSV</Button>
            {hasRole("agent") && <Button onClick={() => setShowCreate(true)}>New Lead</Button>}
          </>
        }
      />

      <Card className="mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input label="Search" placeholder="Name / phone / area" value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} />
          <Select label="Status" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
          </Select>
          <Select label="Source" value={draft.source} onChange={(e) => setDraft({ ...draft, source: e.target.value })}>
            <option value="">All sources</option>
            {SOURCES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
          </Select>
          <div className="grid grid-cols-2 gap-2">
            <Input label="Score min" type="number" min={0} max={100} value={draft.score_min} onChange={(e) => setDraft({ ...draft, score_min: e.target.value })} />
            <Input label="Score max" type="number" min={0} max={100} value={draft.score_max} onChange={(e) => setDraft({ ...draft, score_max: e.target.value })} />
          </div>
          <Input label="From date" type="date" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} />
          <Input label="To date" type="date" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} />
          <div className="flex items-end gap-2">
            <Button onClick={applyFilters}>Apply</Button>
            <Button variant="secondary" onClick={clearFilters}>Clear</Button>
          </div>
        </div>
      </Card>

      <Card>
        {isLoading && <LoadingBlock />}
        {isError && <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div>}
        {data && data.items.length === 0 && (
          <div className="p-6"><EmptyState title="No leads found" hint="Adjust filters or import a CSV." /></div>
        )}
        {data && data.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Phone</th>
                    <th className="px-4 py-3">Location</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Score</th>
                    <th className="px-4 py-3">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((l) => (
                    <tr key={l.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <Link to={`/leads/${l.id}`} className="font-medium text-brand-700 hover:underline">
                          {l.name || "Unnamed"}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{l.phone_number}</td>
                      <td className="px-4 py-3 text-slate-600">{l.preferred_location || l.city || "—"}</td>
                      <td className="px-4 py-3"><LeadStatusBadge status={l.status} /></td>
                      <td className="px-4 py-3 text-slate-600">{titleCase(l.source)}</td>
                      <td className="px-4 py-3"><ScoreBadge score={l.qualification_score} /></td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(l.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
        {isFetching && !isLoading && (
          <div className="px-4 py-2 text-xs text-slate-400">Updating…</div>
        )}
      </Card>

      {showCreate && <CreateLeadModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateLeadModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: "", phone_number: "", city: "", preferred_location: "" });
  const [err, setErr] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () =>
      api.post<Lead>("/leads", {
        name: form.name || null,
        phone_number: form.phone_number,
        city: form.city || null,
        preferred_location: form.preferred_location || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      onClose();
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "Failed"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-md p-6" >
        <div onClick={(e) => e.stopPropagation()}>
          <h2 className="mb-4 text-lg font-semibold">New Lead</h2>
          <div className="space-y-3">
            <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input label="Phone (E.164)" placeholder="+9198XXXXXXXX" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
            <Input label="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
            <Input label="Preferred location" value={form.preferred_location} onChange={(e) => setForm({ ...form, preferred_location: e.target.value })} />
            {err && <p className="text-sm text-red-600">{err}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button onClick={() => mut.mutate()} disabled={!form.phone_number || mut.isPending}>Create</Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
