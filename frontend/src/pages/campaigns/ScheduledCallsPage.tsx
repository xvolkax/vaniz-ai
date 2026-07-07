import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";
import { Card, PageHeader } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState } from "@/components/ui/Bits";
import { CAMPAIGNS_SUBNAV } from "./CampaignsPage";
import { AppointmentStatusBadge } from "@/components/StatusBadges";
import { formatDateTime } from "@/lib/format";

// Scheduled calls = callback appointments Priya committed to. Sourced from the
// tenant dashboard summary (recent appointments), filtered to callbacks.
export function ScheduledCallsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get<DashboardSummary>("/dashboard/summary"),
  });
  const callbacks = (data?.recent_appointments ?? []).filter((a) => a.type === "callback");

  return (
    <div>
      <PageHeader title="Scheduled Calls" subtitle="Callbacks Priya has committed to" />
      <SubNav items={CAMPAIGNS_SUBNAV} />

      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-400">Loading…</Card>
      ) : callbacks.length === 0 ? (
        <EmptyState icon="clock" title="No scheduled callbacks" hint="When a lead asks Priya to call back later, it appears here." />
      ) : (
        <Card>
          <div className="divide-y divide-slate-100">
            {callbacks.map((a) => (
              <div key={a.id} className="flex items-center gap-3 px-5 py-4">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
                  <Icon name="clock" className="h-5 w-5" />
                </span>
                <div className="flex-1">
                  <p className="font-semibold text-slate-800">{a.lead_name || "Lead"}</p>
                  <p className="text-xs text-slate-400">{formatDateTime(a.scheduled_at)}</p>
                </div>
                <AppointmentStatusBadge status={a.status} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
