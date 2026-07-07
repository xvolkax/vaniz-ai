import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardSummary, AppointmentType } from "@/lib/types";
import { Card, PageHeader, Button } from "@/components/ui/Primitives";
import { StatCard } from "@/components/ui/StatCard";
import { Icon, type IconName } from "@/components/ui/Icon";
import { EmptyState, Skeleton } from "@/components/ui/Bits";
import { ErrorState } from "@/components/ui/States";
import { AppointmentStatusBadge } from "@/components/StatusBadges";
import { formatDateTime, titleCase, initials } from "@/lib/format";

const FILTERS: { key: AppointmentType | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "site_visit", label: "Site Visits" },
  { key: "callback", label: "Callbacks" },
  { key: "agent_transfer", label: "Transfers" },
];

const TYPE_ICON: Record<AppointmentType, IconName> = {
  site_visit: "home",
  callback: "clock",
  agent_transfer: "users",
};

export function AppointmentsPage() {
  const [filter, setFilter] = useState<AppointmentType | "all">("all");
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get<DashboardSummary>("/dashboard/summary"),
  });

  const all = data?.recent_appointments ?? [];
  const shown = filter === "all" ? all : all.filter((a) => a.type === filter);
  const siteVisits = all.filter((a) => a.type === "site_visit").length;
  const callbacks = all.filter((a) => a.type === "callback").length;

  return (
    <div>
      <PageHeader title="Appointments" subtitle="Site visits and callbacks Priya has booked for you" />

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard label="Site Visits Booked" value={data?.site_visits_booked ?? siteVisits} icon="home" accent="emerald" loading={isLoading} hint="this month" />
        <StatCard label="Callbacks" value={data?.callback_requests ?? callbacks} icon="clock" accent="amber" loading={isLoading} hint="this month" />
        <StatCard label="Recent Activity" value={all.length} icon="calendar" accent="brand" loading={isLoading} hint="last 10" />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${filter === f.key ? "bg-brand-600 text-white shadow-sm" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && <div className="grid gap-3 sm:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}</div>}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && shown.length === 0 && (
        <EmptyState icon="calendar" title="No appointments yet" hint="When Priya books a site visit or callback, it shows up here." action={<Link to="/campaigns/new"><Button><Icon name="rocket" className="h-4 w-4" /> Launch a campaign</Button></Link>} />
      )}

      {shown.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {shown.map((a) => (
            <Card key={a.id} hover className="p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                  <Icon name={TYPE_ICON[a.type]} className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-semibold text-slate-800">{a.lead_name || "Lead"}</p>
                    <AppointmentStatusBadge status={a.status} />
                  </div>
                  <p className="text-xs text-slate-400">{titleCase(a.type)} · {formatDateTime(a.scheduled_at)}</p>
                  {a.location && <p className="mt-0.5 truncate text-xs text-slate-400"><Icon name="target" className="mr-1 inline h-3 w-3" />{a.location}</p>}
                </div>
                {a.lead_id && (
                  <Link to={`/leads?search=${encodeURIComponent(a.lead_name || "")}`} className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-50 text-xs font-bold text-slate-500 hover:bg-brand-50 hover:text-brand-700">
                    {initials(a.lead_name)}
                  </Link>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
        <Icon name="calendar" className="h-4 w-4" /> A full calendar view with Google Calendar sync is on the roadmap.
      </div>
    </div>
  );
}
