import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Campaign, CampaignAnalytics, Lead, Paginated } from "@/lib/types";
import { Card, PageHeader, Button } from "@/components/ui/Primitives";
import { StatCard } from "@/components/ui/StatCard";
import { Icon } from "@/components/ui/Icon";
import { Modal } from "@/components/ui/Drawer";
import { ProgressBar, Skeleton } from "@/components/ui/Bits";
import { ErrorState } from "@/components/ui/States";
import { CampaignStatusBadge } from "@/components/StatusBadges";
import { formatDateTime, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

export function CampaignDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const [showAdd, setShowAdd] = useState(false);

  const campaignQ = useQuery({ queryKey: ["campaign", id], queryFn: () => api.get<Campaign>(`/campaigns/${id}`) });
  const analyticsQ = useQuery({
    queryKey: ["campaign-analytics", id],
    queryFn: () => api.get<CampaignAnalytics>(`/campaigns/${id}/analytics`),
    refetchInterval: 12000,
  });

  const control = useMutation({
    mutationFn: (action: string) => api.post<Campaign>(`/campaigns/${id}/${action}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaign", id] });
      qc.invalidateQueries({ queryKey: ["campaign-analytics", id] });
    },
    onError: (e) => alert(e instanceof Error ? e.message : "Action failed"),
  });

  const c = campaignQ.data;
  const a = analyticsQ.data;
  const status = c?.status;
  const pct = a && a.total_leads > 0 ? Math.round((a.attempted / a.total_leads) * 100) : 0;

  return (
    <div>
      <PageHeader
        title={c?.name || "Campaign"}
        subtitle={c ? `Created ${formatDateTime(c.created_at)}` : undefined}
        actions={
          <>
            <Link to="/campaigns"><Button variant="ghost">Back</Button></Link>
            {hasRole("agent") && c && (
              <>
                {(status === "draft" || status === "failed") && <Button variant="success" onClick={() => control.mutate("start")} disabled={control.isPending}><Icon name="play" className="h-4 w-4" /> Start</Button>}
                {status === "running" && <Button variant="secondary" onClick={() => control.mutate("pause")} disabled={control.isPending}>Pause</Button>}
                {status === "paused" && <Button variant="success" onClick={() => control.mutate("resume")} disabled={control.isPending}>Resume</Button>}
                {(status === "running" || status === "paused" || status === "draft") && (
                  <>
                    <Button variant="secondary" onClick={() => setShowAdd(true)}><Icon name="plus" className="h-4 w-4" /> Add leads</Button>
                    <Button variant="danger" onClick={() => confirm("Stop this campaign?") && control.mutate("stop")} disabled={control.isPending}>Stop</Button>
                  </>
                )}
              </>
            )}
          </>
        }
      />

      {campaignQ.isLoading && <Skeleton className="h-24 w-full rounded-2xl" />}
      {campaignQ.isError && <ErrorState error={campaignQ.error} onRetry={campaignQ.refetch} />}

      {c && (
        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex flex-wrap items-center gap-4">
              <CampaignStatusBadge status={c.status} />
              <span className="text-sm text-slate-500">Concurrency <b className="text-slate-700">{c.concurrency}</b></span>
              <span className="text-sm text-slate-500">Retries <b className="text-slate-700">{c.max_attempts}</b></span>
              <span className="text-sm text-slate-500">Retry delay <b className="text-slate-700">{c.retry_delay_minutes}m</b></span>
              <span className="text-sm text-slate-500">Hours <b className="text-slate-700">{c.working_hours_start}:00–{c.working_hours_end}:00</b></span>
            </div>
            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs text-slate-500"><span>Leads processed</span><span className="font-semibold">{pct}%</span></div>
              <ProgressBar value={pct} tone={c.status === "running" ? "emerald" : "brand"} />
            </div>
          </Card>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            <StatCard label="Total Leads" value={a?.total_leads ?? "—"} icon="users" accent="slate" loading={analyticsQ.isLoading} />
            <StatCard label="Attempted" value={a?.attempted ?? "—"} icon="phone-outgoing" accent="brand" loading={analyticsQ.isLoading} />
            <StatCard label="Connected" value={a?.connected ?? "—"} icon="phone-incoming" accent="cyan" loading={analyticsQ.isLoading} />
            <StatCard label="Interested" value={a?.interested ?? "—"} icon="sparkles" accent="amber" loading={analyticsQ.isLoading} />
            <StatCard label="Site Visits" value={a?.site_visits ?? "—"} icon="calendar" accent="emerald" loading={analyticsQ.isLoading} />
            <StatCard label="Conversion" value={a ? `${a.conversion_rate}%` : "—"} icon="target" accent="rose" loading={analyticsQ.isLoading} />
          </div>

          <Card className="p-5">
            <h3 className="mb-3 font-bold text-slate-900">Target Breakdown</h3>
            {a && Object.keys(a.status_breakdown).length > 0 ? (
              <div className="flex flex-wrap gap-3">
                {Object.entries(a.status_breakdown).map(([k, v]) => (
                  <div key={k} className="rounded-xl border border-slate-200 px-4 py-2">
                    <p className="text-xs text-slate-400">{titleCase(k)}</p>
                    <p className="text-lg font-bold text-slate-800">{v}</p>
                  </div>
                ))}
                <div className="rounded-xl border border-slate-200 px-4 py-2">
                  <p className="text-xs text-slate-400">Callbacks</p>
                  <p className="text-lg font-bold text-slate-800">{a.callbacks}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No targets yet. Add leads to get started.</p>
            )}
          </Card>
        </div>
      )}

      {showAdd && <AddLeadsModal campaignId={id} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

function AddLeadsModal({ campaignId, onClose }: { campaignId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const leadsQ = useQuery({
    queryKey: ["leads-picker-add"],
    queryFn: () => api.get<Paginated<Lead>>("/leads", { query: { limit: 60, offset: 0, sort_by: "created_at", order: "desc" } }),
  });
  const mut = useMutation({
    mutationFn: () => api.post(`/campaigns/${campaignId}/leads`, { lead_ids: Array.from(selected) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["campaign-analytics", campaignId] }); onClose(); },
    onError: (e) => alert(e instanceof Error ? e.message : "Failed"),
  });
  const toggle = (id: string) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  return (
    <Modal open onClose={onClose} title="Add leads to campaign">
      <div className="max-h-80 overflow-y-auto rounded-xl border border-slate-200">
        {leadsQ.isLoading ? <div className="p-4 text-sm text-slate-400">Loading…</div> :
          leadsQ.data?.items.map((l) => (
            <label key={l.id} className="flex cursor-pointer items-center gap-3 border-b border-slate-100 px-4 py-2.5 text-sm last:border-0 hover:bg-slate-50">
              <input type="checkbox" checked={selected.has(l.id)} onChange={() => toggle(l.id)} className="h-4 w-4 rounded border-slate-300 text-brand-600" />
              <span className="font-medium text-slate-800">{l.name || l.phone_number}</span>
              <span className="text-slate-400">{l.phone_number}</span>
            </label>
          ))}
      </div>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-sm text-slate-500">{selected.size} selected</span>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={selected.size === 0 || mut.isPending}>Add leads</Button>
        </div>
      </div>
    </Modal>
  );
}
