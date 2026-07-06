import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { LeadDetail, LeadStatus } from "@/lib/types";
import { Button, Card, PageHeader, Select } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import {
  AppointmentStatusBadge,
  LeadStatusBadge,
  OutcomeBadge,
  ScoreBadge,
} from "@/components/StatusBadges";
import { formatDateTime, formatDuration, formatInr, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const STATUSES: LeadStatus[] = ["new", "qualifying", "qualified", "unqualified", "booked", "lost"];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-800">{value ?? "—"}</dd>
    </div>
  );
}

export function LeadDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const [status, setStatus] = useState<LeadStatus | "">("");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => api.get<LeadDetail>(`/leads/${id}`),
  });

  const updateMut = useMutation({
    mutationFn: (s: LeadStatus) => api.patch<LeadDetail>(`/leads/${id}`, { status: s }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lead", id] }),
  });

  const callMut = useMutation({
    mutationFn: () =>
      api.post("/calls/outbound", {
        phone_number: data?.phone_number,
        lead_name: data?.name || undefined,
      }),
    onSuccess: () => alert("Outbound call queued."),
    onError: (e) => alert(e instanceof Error ? e.message : "Call failed"),
  });

  const deleteMut = useMutation({
    mutationFn: () => api.del(`/leads/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      navigate("/leads");
    },
    onError: (e) => alert(e instanceof Error ? e.message : "Delete failed"),
  });

  return (
    <div>
      <PageHeader
        title={data?.name || "Lead"}
        subtitle={data?.phone_number}
        actions={
          <>
            <Link to="/leads"><Button variant="secondary">Back</Button></Link>
            {hasRole("agent") && (
              <Button onClick={() => callMut.mutate()} disabled={callMut.isPending || !data}>
                Call now
              </Button>
            )}
            {hasRole("admin") && (
              <Button
                variant="danger"
                onClick={() => confirm("Delete this lead?") && deleteMut.mutate()}
                disabled={deleteMut.isPending}
              >
                Delete
              </Button>
            )}
          </>
        }
      />

      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="p-5 lg:col-span-2">
            <div className="mb-4 flex items-center gap-3">
              <LeadStatusBadge status={data.status} />
              <ScoreBadge score={data.qualification_score} />
              <span className="text-sm text-slate-500">{titleCase(data.source)}</span>
            </div>
            <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <Field label="City" value={data.city} />
              <Field label="Preferred Location" value={data.preferred_location} />
              <Field label="Property Type" value={titleCase(data.property_type || "")} />
              <Field label="Budget Min" value={formatInr(data.budget_min)} />
              <Field label="Budget Max" value={formatInr(data.budget_max)} />
              <Field label="Timeline" value={data.buying_timeline} />
              <Field label="Purpose" value={titleCase(data.purpose || "")} />
              <Field label="Loan Required" value={data.loan_required == null ? "—" : data.loan_required ? "Yes" : "No"} />
              <Field label="Site Visit Interest" value={data.site_visit_interest == null ? "—" : data.site_visit_interest ? "Yes" : "No"} />
              <Field label="Language" value={data.preferred_language} />
              <Field label="Created" value={formatDateTime(data.created_at)} />
              <Field label="Updated" value={formatDateTime(data.updated_at)} />
            </dl>

            {hasRole("agent") && (
              <div className="mt-5 flex items-end gap-2 border-t border-slate-100 pt-4">
                <Select label="Update status" value={status} onChange={(e) => setStatus(e.target.value as LeadStatus)} className="max-w-xs">
                  <option value="">Choose…</option>
                  {STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
                </Select>
                <Button disabled={!status || updateMut.isPending} onClick={() => status && updateMut.mutate(status)}>Save</Button>
              </div>
            )}
          </Card>

          <div className="space-y-6">
            <Card>
              <h2 className="border-b border-slate-100 px-4 py-3 font-semibold text-slate-800">Appointments</h2>
              <div className="divide-y divide-slate-100">
                {data.appointments.length === 0 && <p className="p-4 text-sm text-slate-500">None.</p>}
                {data.appointments.map((a) => (
                  <div key={a.id} className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{titleCase(a.type)}</span>
                      <AppointmentStatusBadge status={a.status} />
                    </div>
                    <p className="text-xs text-slate-500">{formatDateTime(a.scheduled_at)}</p>
                    {a.location && <p className="text-xs text-slate-500">{a.location}</p>}
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <h2 className="border-b border-slate-100 px-4 py-3 font-semibold text-slate-800">Calls</h2>
              <div className="divide-y divide-slate-100">
                {data.calls.length === 0 && <p className="p-4 text-sm text-slate-500">None.</p>}
                {data.calls.map((c) => (
                  <Link key={c.id} to={`/calls/${c.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50">
                    <div>
                      <p className="text-sm">{titleCase(c.direction)} · {formatDuration(c.duration_seconds)}</p>
                      <p className="text-xs text-slate-500">{formatDateTime(c.started_at)}</p>
                    </div>
                    <OutcomeBadge outcome={c.outcome} />
                  </Link>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
