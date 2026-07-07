import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsOverview, BreakdownResponse, ConversionTrends } from "@/lib/types";
import { Card, PageHeader } from "@/components/ui/Primitives";
import { StatCard } from "@/components/ui/StatCard";
import { Icon } from "@/components/ui/Icon";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import { titleCase, formatMoney } from "@/lib/format";

const RATE_PER_MIN = 6;
const RANGES = [7, 30, 90];
const OUTCOME_COLORS: Record<string, string> = {
  completed: "#10b981",
  callback_requested: "#f59e0b",
  transfer_requested: "#8b5cf6",
  not_interested: "#94a3b8",
  no_answer: "#f43f5e",
  failed: "#ef4444",
  voicemail: "#22d3ee",
};

export function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const overview = useQuery({ queryKey: ["analytics-overview", days], queryFn: () => api.get<AnalyticsOverview>("/analytics/overview", { query: { days } }) });
  const outcomes = useQuery({ queryKey: ["analytics-outcomes", days], queryFn: () => api.get<BreakdownResponse>("/analytics/call-outcomes", { query: { days } }) });
  const sources = useQuery({ queryKey: ["analytics-sources", days], queryFn: () => api.get<BreakdownResponse>("/analytics/lead-sources", { query: { days } }) });
  const trends = useQuery({ queryKey: ["analytics-trends", days], queryFn: () => api.get<ConversionTrends>("/analytics/conversion-trends", { query: { days } }) });

  const ov = overview.data;
  const minutes = ov && ov.avg_call_duration_seconds != null ? Math.round((ov.total_calls * ov.avg_call_duration_seconds) / 60) : null;
  const costPerAppt = ov && ov.site_visits > 0 && minutes != null ? (minutes * RATE_PER_MIN) / ov.site_visits : null;
  const costPerLead = ov && ov.total_leads > 0 && minutes != null ? (minutes * RATE_PER_MIN) / ov.total_leads : null;

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Outcomes that move revenue — not technical noise"
        actions={
          <div className="flex rounded-xl bg-white p-1 ring-1 ring-slate-200">
            {RANGES.map((r) => (
              <button key={r} onClick={() => setDays(r)} className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${days === r ? "bg-brand-600 text-white" : "text-slate-500 hover:text-slate-800"}`}>{r}d</button>
            ))}
          </div>
        }
      />

      {overview.isError && <ErrorState error={overview.error} onRetry={overview.refetch} />}

      {/* Business outcome KPIs first */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Calls Made" value={ov?.total_calls ?? 0} icon="phone-outgoing" accent="brand" loading={overview.isLoading} />
        <StatCard label="Answer Rate" value={ov ? `${ov.answer_rate}%` : "—"} icon="target" accent="cyan" loading={overview.isLoading} />
        <StatCard label="Conversion Rate" value={ov ? `${ov.conversion_rate}%` : "—"} icon="bolt" accent="emerald" loading={overview.isLoading} hint="site visits / connected" />
        <StatCard label="Interested Leads" value={ov?.qualified_leads ?? 0} icon="sparkles" accent="amber" loading={overview.isLoading} />
        <StatCard label="Appointments" value={ov?.site_visits ?? 0} icon="calendar" accent="brand" loading={overview.isLoading} />
        <StatCard label="Callbacks" value={ov?.callbacks ?? 0} icon="clock" accent="slate" loading={overview.isLoading} />
        <StatCard label="Cost / Lead" value={costPerLead != null ? formatMoney(Math.round(costPerLead)) : "—"} icon="users" accent="rose" hint={`est. @ ₹${RATE_PER_MIN}/min`} />
        <StatCard label="Cost / Booking" value={costPerAppt != null ? formatMoney(Math.round(costPerAppt)) : "—"} icon="home" accent="cyan" hint={`est. @ ₹${RATE_PER_MIN}/min`} />
      </div>

      {/* Trends */}
      <Card className="mb-6 p-6">
        <h2 className="mb-4 font-bold text-slate-900">Activity Trends</h2>
        {trends.isLoading ? <LoadingBlock /> : trends.data && (
          <>
            <div className="flex h-56 items-end gap-1">
              {trends.data.points.map((p) => {
                const max = Math.max(1, ...trends.data!.points.map((x) => x.calls));
                const h = (p.calls / max) * 100;
                const sv = p.calls > 0 ? (p.site_visits / p.calls) * 100 : 0;
                return (
                  <div key={p.date} className="group relative flex flex-1 flex-col justify-end" title={`${p.date}\nCalls ${p.calls} · Answered ${p.answered} · Visits ${p.site_visits} · Leads ${p.new_leads}`}>
                    <div className="relative w-full overflow-hidden rounded-t-md bg-brand-100" style={{ height: `${Math.max(2, h)}%` }}>
                      <div className="absolute bottom-0 w-full bg-gradient-to-t from-emerald-500 to-emerald-400" style={{ height: `${sv}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand-200" /> Calls</span>
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" /> Site visits (share of calls)</span>
            </div>
          </>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Outcomes donut */}
        <Card className="p-6">
          <h2 className="mb-4 font-bold text-slate-900">Call Outcomes</h2>
          {outcomes.isLoading ? <LoadingBlock /> : outcomes.data && outcomes.data.total === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">No calls in this period.</p>
          ) : outcomes.data && (
            <div className="flex items-center gap-6">
              <Donut items={outcomes.data.items.map((i) => ({ label: i.key, value: i.count, color: OUTCOME_COLORS[i.key] || "#cbd5e1" }))} total={outcomes.data.total} />
              <div className="flex-1 space-y-2">
                {outcomes.data.items.map((i) => (
                  <div key={i.key} className="flex items-center gap-2 text-sm">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: OUTCOME_COLORS[i.key] || "#cbd5e1" }} />
                    <span className="flex-1 text-slate-600">{titleCase(i.key)}</span>
                    <span className="font-semibold text-slate-800">{i.count}</span>
                    <span className="w-10 text-right text-xs text-slate-400">{i.percentage}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Lead sources */}
        <Card className="p-6">
          <h2 className="mb-4 font-bold text-slate-900">Where Leads Come From</h2>
          {sources.isLoading ? <LoadingBlock /> : sources.data && sources.data.total === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">No leads in this period.</p>
          ) : sources.data && (
            <div className="space-y-3">
              {sources.data.items.map((i) => (
                <div key={i.key}>
                  <div className="mb-1 flex justify-between text-sm"><span className="text-slate-600">{titleCase(i.key)}</span><span className="text-slate-400">{i.count} · {i.percentage}%</span></div>
                  <div className="h-2.5 w-full rounded-full bg-slate-100"><div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500" style={{ width: `${i.percentage}%` }} /></div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-6 flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-500">
        <Icon name="chart" className="h-4 w-4" /> Revenue attribution (deal value linked to booked visits) is coming soon.
      </div>
    </div>
  );
}

function Donut({ items, total }: { items: { label: string; value: number; color: string }[]; total: number }) {
  let acc = 0;
  const stops = items
    .filter((i) => i.value > 0)
    .map((i) => {
      const start = (acc / Math.max(1, total)) * 360;
      acc += i.value;
      const end = (acc / Math.max(1, total)) * 360;
      return `${i.color} ${start}deg ${end}deg`;
    })
    .join(", ");
  return (
    <div className="relative h-32 w-32 shrink-0">
      <div className="h-full w-full rounded-full" style={{ background: stops ? `conic-gradient(${stops})` : "#e2e8f0" }} />
      <div className="absolute inset-[18%] flex flex-col items-center justify-center rounded-full bg-white">
        <span className="text-xl font-bold text-slate-900">{total}</span>
        <span className="text-[10px] uppercase text-slate-400">calls</span>
      </div>
    </div>
  );
}
