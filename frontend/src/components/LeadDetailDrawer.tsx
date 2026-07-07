import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { LeadDetail, LeadStatus } from "@/lib/types";
import { Drawer } from "@/components/ui/Drawer";
import { Button, Select } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Bits";
import { LeadStatusBadge, TemperatureBadge, OutcomeBadge } from "@/components/StatusBadges";
import { formatMoney, formatDateTime, formatDuration, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const STATUSES: LeadStatus[] = ["new", "qualifying", "qualified", "unqualified", "booked", "lost"];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-white p-3 ring-1 ring-slate-100">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-slate-800">{value ?? "—"}</p>
    </div>
  );
}

export function LeadDetailDrawer({ leadId, onClose }: { leadId: string | null; onClose: () => void }) {
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const [status, setStatus] = useState<LeadStatus | "">("");

  const { data, isLoading } = useQuery({
    queryKey: ["lead", leadId],
    queryFn: () => api.get<LeadDetail>(`/leads/${leadId}`),
    enabled: !!leadId,
  });

  const update = useMutation({
    mutationFn: (s: LeadStatus) => api.patch(`/leads/${leadId}`, { status: s }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lead", leadId] }); qc.invalidateQueries({ queryKey: ["leads"] }); },
  });
  const call = useMutation({
    mutationFn: () => api.post("/calls/outbound", { phone_number: data?.phone_number, lead_name: data?.name || undefined }),
    onSuccess: () => alert("Outbound call queued."),
    onError: (e) => alert(e instanceof Error ? e.message : "Call failed"),
  });

  return (
    <Drawer
      open={!!leadId}
      onClose={onClose}
      title={data?.name || "Lead"}
      subtitle={data?.phone_number}
      footer={
        hasRole("agent") && data ? (
          <div className="flex items-center gap-2">
            <Select value={status} onChange={(e) => setStatus(e.target.value as LeadStatus)} className="flex-1">
              <option value="">Change status…</option>
              {STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
            </Select>
            <Button variant="secondary" disabled={!status || update.isPending} onClick={() => status && update.mutate(status)}>Save</Button>
            <Button disabled={call.isPending} onClick={() => call.mutate()}><Icon name="phone" className="h-4 w-4" /> Call now</Button>
          </div>
        ) : undefined
      }
    >
      {isLoading || !data ? (
        <div className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-32" /></div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <LeadStatusBadge status={data.status} />
            <TemperatureBadge score={data.qualification_score} />
            <span className="text-sm text-slate-400">Score {data.qualification_score ?? "—"} · {titleCase(data.source)}</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Budget" value={data.budget_max ? `${formatMoney(data.budget_min)} – ${formatMoney(data.budget_max)}` : formatMoney(data.budget_max)} />
            <Field label="Location" value={data.preferred_location || data.city} />
            <Field label="Property Type" value={titleCase(data.property_type || "")} />
            <Field label="Timeline" value={data.buying_timeline} />
            <Field label="Purpose" value={titleCase(data.purpose || "")} />
            <Field label="Loan" value={data.loan_required == null ? "—" : data.loan_required ? "Required" : "No"} />
          </div>

          <div className="card p-4">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Appointments</h4>
            {data.appointments.length === 0 ? <p className="text-sm text-slate-400">None yet.</p> : (
              <div className="space-y-2">
                {data.appointments.map((a) => (
                  <div key={a.id} className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{titleCase(a.type)}</span>
                    <span className="text-slate-400">{formatDateTime(a.scheduled_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card p-4">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Call history</h4>
            {data.calls.length === 0 ? <p className="text-sm text-slate-400">No calls yet.</p> : (
              <div className="space-y-2">
                {data.calls.map((c) => (
                  <div key={c.id} className="flex items-center justify-between text-sm">
                    <span className="text-slate-600">{titleCase(c.direction)} · {formatDuration(c.duration_seconds)}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">{formatDateTime(c.started_at)}</span>
                      <OutcomeBadge outcome={c.outcome} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
