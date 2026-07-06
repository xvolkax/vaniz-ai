import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";
import { Card, PageHeader } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { AppointmentStatusBadge } from "@/components/StatusBadges";
import { formatDateTime, titleCase } from "@/lib/format";

// NOTE: the backend exposes no dedicated /appointments list endpoint. The only
// tenant-scoped appointment feed available is DashboardSummary.recent_appointments
// (10 most recent). We use that here rather than inventing an endpoint.
export function AppointmentsPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get<DashboardSummary>("/dashboard/summary"),
  });

  return (
    <div>
      <PageHeader title="Appointments" subtitle="10 most recent site visits, callbacks & transfers" />
      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && data.recent_appointments.length === 0 && (
        <EmptyState title="No appointments yet" hint="Appointments booked by the AI will appear here." />
      )}
      {data && data.recent_appointments.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Lead</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Scheduled</th>
                  <th className="px-4 py-3">Location</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.recent_appointments.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      {a.lead_id ? (
                        <Link to={`/leads/${a.lead_id}`} className="font-medium text-brand-700 hover:underline">
                          {a.lead_name || "Lead"}
                        </Link>
                      ) : (
                        a.lead_name || "Lead"
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{titleCase(a.type)}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(a.scheduled_at)}</td>
                    <td className="px-4 py-3 text-slate-600">{a.location || "—"}</td>
                    <td className="px-4 py-3"><AppointmentStatusBadge status={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
