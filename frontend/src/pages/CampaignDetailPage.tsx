import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Campaign, CampaignAnalytics, Lead, Paginated } from "@/lib/types";
import { Button, Card, PageHeader } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import { CampaignStatusBadge } from "@/components/StatusBadges";
import { formatDateTime, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </Card>
  );
}

export function CampaignDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const [showAdd, setShowAdd] = useState(false);

  const campaignQ = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => api.get<Campaign>(`/campaigns/${id}`),
  });
  const analyticsQ = useQuery({
    queryKey: ["campaign-analytics", id],
    queryFn: () => api.get<CampaignAnalytics>(`/campaigns/${id}/analytics`),
    refetchInterval: 15_000,
  });

  const control = useMutation({
    mutationFn: (action: "start" | "pause" | "resume" | "stop") =>
      api.post<Campaign>(`/campaigns/${id}/${action}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaign", id] });
      qc.invalidateQueries({ queryKey: ["campaign-analytics", id] });
    },
    onError: (e) => alert(e instanceof Error ? e.message : "Action failed"),
  });

  const c = campaignQ.data;
  const status = c?.status;

  return (
    <div>
      <PageHeader
        title={c?.name || "Campaign"}
        subtitle={c ? `Created ${formatDateTime(c.created_at)}` : undefined}
        actions={
          <>
            <Link to="/campaigns"><Button variant="secondary">Back</Button></Link>
            {hasRole("agent") && c && (
              <>
                {(status === "draft" || status === "failed") && (
                  <Button onClick={() => control.mutate("start")} disabled={control.isPending}>Start</Button>
                )}
                {status === "running" && (
                  <Button variant="secondary" onClick={() => control.mutate("pause")} disabled={control.isPending}>Pause</Button>
                )}
                {status === "paused" && (
                  <Button onClick={() => control.mutate("resume")} disabled={control.isPending}>Resume</Button>
                )}
                {(status === "running" || status === "paused" || status === "draft") && (
                  <Button variant="danger" onClick={() => confirm("Stop campaign?") && control.mutate("stop")} disabled={control.isPending}>Stop</Button>
                )}
                {status !== "completed" && status !== "failed" && (
                  <Button variant="secondary" onClick={() => setShowAdd(true)}>Add leads</Button>
                )}
              </>
            )}
          </>
        }
      />

      {campaignQ.isLoading && <LoadingBlock />}
      {campaignQ.isError && <ErrorState error={campaignQ.error} onRetry={campaignQ.refetch} />}

      {c && (
        <div className="space-y-6">
          <Card className="flex flex-wrap items-center gap-6 p-4">
            <CampaignStatusBadge status={c.status} />
            <span className="text-sm text-slate-600">Concurrency: <b>{c.concurrency}</b></span>
            <span className="text-sm text-slate-600">Max attempts: <b>{c.max_attempts}</b></span>
            <span className="text-sm text-slate-600">Retry delay: <b>{c.retry_delay_minutes}m</b></span>
            <span className="text-sm text-slate-600">Working hours: <b>{c.working_hours_start}:00–{c.working_hours_end}:00</b></span>
            {c.started_at && <span className="text-sm text-slate-600">Started: <b>{formatDateTime(c.started_at)}</b></span>}
          </Card>

          <div>
            <h2 className="mb-3 font-semibold text-slate-800">Analytics</h2>
            {analyticsQ.isLoading && <LoadingBlock />}
            {analyticsQ.data && (
              <>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
                  <Stat label="Total Leads" value={analyticsQ.data.total_leads} />
                  <Stat label="Attempted" value={analyticsQ.data.attempted} />
                  <Stat label="Connected" value={analyticsQ.data.connected} />
                  <Stat label="Interested" value={analyticsQ.data.interested} />
                  <Stat label="Callbacks" value={analyticsQ.data.callbacks} />
                  <Stat label="Site Visits" value={analyticsQ.data.site_visits} />
                  <Stat label="Conversion" value={`${analyticsQ.data.conversion_rate}%`} />
                </div>
                <Card className="mt-4 p-4">
                  <h3 className="mb-2 text-sm font-medium text-slate-700">Target status breakdown</h3>
                  <div className="flex flex-wrap gap-3">
                    {Object.entries(analyticsQ.data.status_breakdown).map(([k, v]) => (
                      <span key={k} className="rounded-md bg-slate-100 px-3 py-1 text-sm text-slate-700">
                        {titleCase(k)}: <b>{v}</b>
                      </span>
                    ))}
                    {Object.keys(analyticsQ.data.status_breakdown).length === 0 && (
                      <span className="text-sm text-slate-500">No targets yet.</span>
                    )}
                  </div>
                </Card>
              </>
            )}
          </div>
        </div>
      )}

      {showAdd && <AddLeadsModal campaignId={id} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

function AddLeadsModal({ campaignId, onClose }: { campaignId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);

  const leadsQ = useQuery({
    queryKey: ["leads-picker"],
    queryFn: () => api.get<Paginated<Lead>>("/leads", { query: { limit: 50, offset: 0, sort_by: "created_at", order: "desc" } }),
  });

  const mut = useMutation({
    mutationFn: () => api.post(`/campaigns/${campaignId}/leads`, { lead_ids: Array.from(selected) }),
    onSuccess: (res: unknown) => {
      const added = (res as { added?: number })?.added ?? 0;
      alert(`Added ${added} lead(s).`);
      qc.invalidateQueries({ queryKey: ["campaign-analytics", campaignId] });
      onClose();
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "Failed"),
  });

  function toggle(idv: string) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(idv)) next.delete(idv);
      else next.add(idv);
      return next;
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <Card className="flex max-h-[80vh] w-full max-w-lg flex-col p-6">
        <div className="flex min-h-0 flex-col" onClick={(e) => e.stopPropagation()}>
          <h2 className="mb-1 text-lg font-semibold">Add Leads</h2>
          <p className="mb-3 text-sm text-slate-500">Latest 50 leads. Select to add as targets.</p>
          <div className="min-h-0 flex-1 overflow-y-auto rounded-md border border-slate-200">
            {leadsQ.isLoading && <LoadingBlock />}
            {leadsQ.data?.items.map((l) => (
              <label key={l.id} className="flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2 text-sm hover:bg-slate-50">
                <input type="checkbox" checked={selected.has(l.id)} onChange={() => toggle(l.id)} />
                <span className="font-medium">{l.name || l.phone_number}</span>
                <span className="text-slate-500">{l.phone_number}</span>
              </label>
            ))}
          </div>
          {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-slate-500">{selected.size} selected</span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button onClick={() => mut.mutate()} disabled={selected.size === 0 || mut.isPending}>Add</Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
