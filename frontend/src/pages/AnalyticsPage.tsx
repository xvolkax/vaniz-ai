import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AnalyticsOverview,
  BreakdownResponse,
  ConversionTrends,
} from "@/lib/types";
import { Card, PageHeader, Select } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import { titleCase } from "@/lib/format";

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </Card>
  );
}

function Breakdown({ title, query, days }: { title: string; query: string; days: number }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: [query, days],
    queryFn: () => api.get<BreakdownResponse>(query, { query: { days } }),
  });
  return (
    <Card className="p-4">
      <h3 className="mb-3 font-semibold text-slate-800">{title}</h3>
      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && data.items.length === 0 && <p className="text-sm text-slate-500">No data.</p>}
      {data && data.items.length > 0 && (
        <div className="space-y-2">
          {data.items.map((it) => (
            <div key={it.key}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-slate-700">{titleCase(it.key)}</span>
                <span className="text-slate-500">{it.count} · {it.percentage}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-brand-500" style={{ width: `${it.percentage}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function TrendsChart({ days }: { days: number }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["conversion-trends", days],
    queryFn: () => api.get<ConversionTrends>("/analytics/conversion-trends", { query: { days } }),
  });
  return (
    <Card className="p-4">
      <h3 className="mb-3 font-semibold text-slate-800">Conversion Trends</h3>
      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && (
        <>
          <div className="flex h-48 items-end gap-1 overflow-x-auto">
            {data.points.map((p) => {
              const max = Math.max(1, ...data.points.map((x) => x.calls));
              const h = (p.calls / max) * 100;
              const sv = p.calls > 0 ? (p.site_visits / p.calls) * 100 : 0;
              return (
                <div key={p.date} className="group relative flex min-w-[8px] flex-1 flex-col justify-end" title={`${p.date}: ${p.calls} calls, ${p.answered} answered, ${p.site_visits} visits, ${p.new_leads} leads`}>
                  <div className="relative w-full rounded-t bg-brand-100" style={{ height: `${h}%` }}>
                    <div className="absolute bottom-0 w-full rounded-t bg-brand-500" style={{ height: `${sv}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-brand-100" /> Calls</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-brand-500" /> Site visits (share)</span>
          </div>
        </>
      )}
    </Card>
  );
}

export function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const overview = useQuery({
    queryKey: ["analytics-overview", days],
    queryFn: () => api.get<AnalyticsOverview>("/analytics/overview", { query: { days } }),
  });

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle={`Last ${days} days`}
        actions={
          <Select value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-40">
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </Select>
        }
      />

      {overview.isLoading && <LoadingBlock />}
      {overview.isError && <ErrorState error={overview.error} onRetry={overview.refetch} />}
      {overview.data && (
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          <Kpi label="Total Calls" value={overview.data.total_calls} />
          <Kpi label="Answered" value={overview.data.answered_calls} />
          <Kpi label="Answer Rate" value={`${overview.data.answer_rate}%`} />
          <Kpi label="Total Leads" value={overview.data.total_leads} />
          <Kpi label="Qualified" value={overview.data.qualified_leads} />
          <Kpi label="Hot Leads" value={overview.data.hot_leads} />
          <Kpi label="Site Visits" value={overview.data.site_visits} />
          <Kpi label="Callbacks" value={overview.data.callbacks} />
          <Kpi label="Conversion" value={`${overview.data.conversion_rate}%`} />
          <Kpi label="Avg Score" value={overview.data.avg_qualification_score ?? "—"} />
          <Kpi label="Avg Duration" value={overview.data.avg_call_duration_seconds ? `${Math.round(overview.data.avg_call_duration_seconds)}s` : "—"} />
          <Kpi label="Avg E2E ms" value={overview.data.avg_e2e_latency_ms ? Math.round(overview.data.avg_e2e_latency_ms) : "—"} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Breakdown title="Call Outcomes" query="/analytics/call-outcomes" days={days} />
        <Breakdown title="Lead Sources" query="/analytics/lead-sources" days={days} />
        <div className="lg:col-span-2">
          <TrendsChart days={days} />
        </div>
      </div>
    </div>
  );
}
