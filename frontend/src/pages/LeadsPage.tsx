import { useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Lead, LeadImportResult, LeadSource, LeadStatus, Paginated } from "@/lib/types";
import { Card, PageHeader, Button, Input, Select, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { Skeleton, EmptyState } from "@/components/ui/Bits";
import { Pagination } from "@/components/ui/Pagination";
import { ErrorState } from "@/components/ui/States";
import { LeadStatusBadge, TemperatureBadge, temperature } from "@/components/StatusBadges";
import { LeadDetailDrawer } from "@/components/LeadDetailDrawer";
import { formatMoney, titleCase, initials, relativeTime } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const STATUSES: LeadStatus[] = ["new", "qualifying", "qualified", "unqualified", "booked", "lost"];
const SOURCES: LeadSource[] = ["inbound_call", "outbound_call", "manual", "csv_import", "api", "other"];
const LIMIT = 24;

const TEMPS = [
  { key: "", label: "All", min: undefined, max: undefined },
  { key: "hot", label: "🔥 Hot", min: 70, max: undefined },
  { key: "warm", label: "🌤 Warm", min: 45, max: 69 },
  { key: "cold", label: "❄ Cold", min: undefined, max: 44 },
] as const;

export function LeadsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [temp, setTemp] = useState("");

  const [draft, setDraft] = useState({
    search: params.get("search") ?? "",
    status: "",
    source: params.get("source") ?? "",
  });
  const [filters, setFilters] = useState(draft);

  const tempRange = TEMPS.find((t) => t.key === temp)!;
  const query = {
    search: filters.search || undefined,
    status: filters.status || undefined,
    source: filters.source || undefined,
    score_min: tempRange.min,
    score_max: tempRange.max,
    limit: LIMIT,
    offset,
  };
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["leads", query],
    queryFn: () => api.get<Paginated<Lead>>("/leads", { query }),
  });

  const importMut = useMutation({
    mutationFn: (file: File) => { const fd = new FormData(); fd.append("file", file); return api.upload<LeadImportResult>("/leads/import", fd); },
    onSuccess: (r) => { alert(`Imported ${r.created} new + ${r.updated} updated. ${r.skipped} skipped.`); qc.invalidateQueries({ queryKey: ["leads"] }); },
    onError: (e) => alert(e instanceof Error ? e.message : "Import failed"),
  });

  function apply() { setOffset(0); setFilters(draft); const p = new URLSearchParams(); if (draft.search) p.set("search", draft.search); if (draft.source) p.set("source", draft.source); setParams(p, { replace: true }); }
  function exportCsv() { void api.download("/leads/export", "leads.csv", { query: { search: query.search, status: query.status, source: query.source, score_min: query.score_min, score_max: query.score_max } }); }

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle={data ? `${data.total} leads in your pipeline` : "Your pipeline"}
        actions={
          <>
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) importMut.mutate(f); e.target.value = ""; }} />
            {hasRole("agent") && <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={importMut.isPending}><Icon name="upload" className="h-4 w-4" /> Import</Button>}
            <Button variant="secondary" onClick={exportCsv}><Icon name="download" className="h-4 w-4" /> Export</Button>
          </>
        }
      />

      {/* Temperature segmentation */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {TEMPS.map((t) => (
          <button key={t.key} onClick={() => { setTemp(t.key); setOffset(0); }}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${temp === t.key ? "bg-brand-600 text-white shadow-sm" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"}`}>
            {t.label}
          </button>
        ))}
      </div>

      <Card className="mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2"><Input label="Search" placeholder="Name, phone or area" value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} /></div>
          <Select label="Status" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
            <option value="">All statuses</option>{STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
          </Select>
          <Select label="Source" value={draft.source} onChange={(e) => setDraft({ ...draft, source: e.target.value })}>
            <option value="">All sources</option>{SOURCES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
          </Select>
        </div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={apply}>Apply</Button>
          <Button size="sm" variant="ghost" onClick={() => { const e = { search: "", status: "", source: "" }; setDraft(e); setFilters(e); setTemp(""); setOffset(0); setParams({}, { replace: true }); }}>Clear</Button>
        </div>
      </Card>

      {isLoading && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-2xl" />)}</div>}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && data.items.length === 0 && <EmptyState icon="users" title="No leads found" hint="Adjust filters or import a CSV to fill your pipeline." />}

      {data && data.items.length > 0 && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((l) => {
              const t = temperature(l.qualification_score);
              return (
                <Card key={l.id} hover className="cursor-pointer p-4" >
                  <div onClick={() => setOpenId(l.id)}>
                    <div className="flex items-start gap-3">
                      <span className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${t.tone === "red" ? "bg-rose-50 text-rose-600" : t.tone === "amber" ? "bg-amber-50 text-amber-600" : "bg-slate-100 text-slate-500"}`}>
                        {initials(l.name || l.phone_number)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold text-slate-900">{l.name || "Unnamed lead"}</p>
                        <p className="truncate text-xs text-slate-400">{l.phone_number}</p>
                      </div>
                      <TemperatureBadge score={l.qualification_score} />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <LeadStatusBadge status={l.status} />
                      {l.property_type && <Badge tone="blue">{titleCase(l.property_type)}</Badge>}
                    </div>
                    <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                      <div><dt className="text-slate-400">Budget</dt><dd className="font-medium text-slate-700">{l.budget_max ? formatMoney(l.budget_max) : "—"}</dd></div>
                      <div><dt className="text-slate-400">Location</dt><dd className="truncate font-medium text-slate-700">{l.preferred_location || l.city || "—"}</dd></div>
                      <div><dt className="text-slate-400">Timeline</dt><dd className="truncate font-medium text-slate-700">{l.buying_timeline || "—"}</dd></div>
                      <div><dt className="text-slate-400">Added</dt><dd className="font-medium text-slate-700">{relativeTime(l.created_at)}</dd></div>
                    </dl>
                  </div>
                </Card>
              );
            })}
          </div>
          <div className="mt-4"><Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} /></div>
        </>
      )}

      <LeadDetailDrawer leadId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
