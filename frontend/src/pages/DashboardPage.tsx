import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";
import { Card, PageHeader } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import { OutcomeBadge, AppointmentStatusBadge, ScoreBadge } from "@/components/StatusBadges";
import { formatDateTime, formatDuration, titleCase } from "@/lib/format";

function Kpi({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </Card>
  );
}

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get<DashboardSummary>("/dashboard/summary"),
  });

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Your workspace at a glance" />
      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Kpi label="Calls Today" value={data.calls_today} />
            <Kpi label="Calls This Month" value={data.calls_this_month} />
            <Kpi label="Answered (Month)" value={data.answered_calls} />
            <Kpi label="Conversion Rate" value={`${data.conversion_rate}%`} hint="Site visits / answered" />
            <Kpi label="Interested Leads" value={data.interested_leads} />
            <Kpi label="Hot Leads" value={data.hot_leads} hint="Score ≥ 70" />
            <Kpi label="Site Visits (Month)" value={data.site_visits_booked} />
            <Kpi label="Callbacks (Month)" value={data.callback_requests} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="font-semibold text-slate-800">Recent Calls</h2>
                <Link to="/calls" className="text-sm text-brand-600 hover:underline">View all</Link>
              </div>
              <div className="divide-y divide-slate-100">
                {data.recent_calls.length === 0 && (
                  <p className="p-4 text-sm text-slate-500">No calls yet.</p>
                )}
                {data.recent_calls.map((c) => (
                  <Link
                    key={c.id}
                    to={`/calls/${c.id}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-800">
                        {c.lead_name || c.phone_number || "Unknown"}
                      </p>
                      <p className="text-xs text-slate-500">
                        {titleCase(c.direction)} · {formatDateTime(c.call_date)} · {formatDuration(c.duration_seconds)}
                      </p>
                    </div>
                    <OutcomeBadge outcome={c.outcome} />
                  </Link>
                ))}
              </div>
            </Card>

            <Card>
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="font-semibold text-slate-800">Recent Appointments</h2>
                <Link to="/appointments" className="text-sm text-brand-600 hover:underline">View all</Link>
              </div>
              <div className="divide-y divide-slate-100">
                {data.recent_appointments.length === 0 && (
                  <p className="p-4 text-sm text-slate-500">No appointments yet.</p>
                )}
                {data.recent_appointments.map((a) => (
                  <div key={a.id} className="flex items-center justify-between px-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-800">
                        {a.lead_name || "Lead"} · {titleCase(a.type)}
                      </p>
                      <p className="text-xs text-slate-500">{formatDateTime(a.scheduled_at)}</p>
                    </div>
                    <AppointmentStatusBadge status={a.status} />
                  </div>
                ))}
              </div>
            </Card>

            <Card className="lg:col-span-2">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="font-semibold text-slate-800">Hot Leads</h2>
                <Link to="/leads?status=qualified" className="text-sm text-brand-600 hover:underline">View leads</Link>
              </div>
              <div className="divide-y divide-slate-100">
                {data.recent_hot_leads.length === 0 && (
                  <p className="p-4 text-sm text-slate-500">No hot leads yet.</p>
                )}
                {data.recent_hot_leads.map((l) => (
                  <Link
                    key={l.id}
                    to={`/leads/${l.id}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-800">
                        {l.name || l.phone_number}
                      </p>
                      <p className="text-xs text-slate-500">
                        {l.preferred_location || l.city || "—"} · {titleCase(l.property_type || "")}
                      </p>
                    </div>
                    <ScoreBadge score={l.qualification_score} />
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
