import { Link } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AnalyticsOverview,
  BreakdownResponse,
  Campaign,
  CampaignAnalytics,
  DashboardSummary,
  Paginated,
} from "@/lib/types";
import { StatCard } from "@/components/ui/StatCard";
import { Card, Button } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { ProgressBar } from "@/components/ui/Bits";
import { ErrorState } from "@/components/ui/States";
import { OutcomeBadge, CampaignStatusBadge, ScorePill } from "@/components/StatusBadges";
import { relativeTime, formatMoney, initials, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const ASSUMED_RATE_PER_MIN = 6; // ₹/min, transparent assumption for cost estimate

export function DashboardPage() {
  const { user } = useAuth();

  const summaryQ = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get<DashboardSummary>("/dashboard/summary"),
  });
  const overviewQ = useQuery({
    queryKey: ["analytics-overview", 30],
    queryFn: () => api.get<AnalyticsOverview>("/analytics/overview", { query: { days: 30 } }),
  });
  const outcomesQ = useQuery({
    queryKey: ["analytics-outcomes", 30],
    queryFn: () => api.get<BreakdownResponse>("/analytics/call-outcomes", { query: { days: 30 } }),
  });
  const campaignsQ = useQuery({
    queryKey: ["campaigns", 0],
    queryFn: () => api.get<Paginated<Campaign>>("/campaigns", { query: { limit: 4, offset: 0 } }),
  });

  const s = summaryQ.data;
  const ov = overviewQ.data;
  const transfers =
    outcomesQ.data?.items.find((i) => i.key === "transfer_requested")?.count ?? null;
  const minutes =
    ov && ov.avg_call_duration_seconds != null
      ? Math.round((ov.total_calls * ov.avg_call_duration_seconds) / 60)
      : null;
  const estCost = minutes != null ? minutes * ASSUMED_RATE_PER_MIN : null;

  const loading = summaryQ.isLoading;

  if (summaryQ.isError) {
    return <ErrorState error={summaryQ.error} onRetry={summaryQ.refetch} />;
  }

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="flex flex-col justify-between gap-4 rounded-2xl bg-gradient-to-br from-brand-600 via-brand-600 to-violet-600 p-6 text-white shadow-pop sm:flex-row sm:items-center">
        <div>
          <p className="text-sm text-white/70">Welcome back{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}</p>
          <h1 className="mt-1 text-2xl font-bold">Here's what Priya did for you</h1>
          <p className="mt-1 text-sm text-white/80">
            Your AI agent calls leads, qualifies them, and books site visits — automatically.
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/campaigns/new">
            <Button variant="secondary" className="!bg-white/15 !text-white !border-white/20 hover:!bg-white/25">
              <Icon name="rocket" className="h-4 w-4" /> Launch Campaign
            </Button>
          </Link>
          <Link to="/leads">
            <Button className="!bg-white !text-brand-700 hover:!bg-white/90">
              <Icon name="upload" className="h-4 w-4" /> Upload Leads
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
        <StatCard label="Today's Calls" value={s?.calls_today ?? 0} icon="phone-outgoing" accent="brand" loading={loading} />
        <StatCard label="Calls Answered (mo.)" value={s?.answered_calls ?? 0} icon="phone-incoming" accent="emerald" loading={loading} />
        <StatCard label="Connected Rate" value={ov ? `${ov.answer_rate}%` : "—"} icon="target" accent="cyan" loading={overviewQ.isLoading} hint="last 30 days" />
        <StatCard label="Interested Leads" value={s?.interested_leads ?? 0} icon="sparkles" accent="amber" loading={loading} />
        <StatCard label="Site Visits Booked" value={s?.site_visits_booked ?? 0} icon="calendar" accent="brand" loading={loading} hint="this month" />
        <StatCard label="Callback Requests" value={s?.callback_requests ?? 0} icon="history" accent="slate" loading={loading} hint="this month" />
        <StatCard label="Human Transfers" value={transfers ?? "—"} icon="users" accent="rose" loading={outcomesQ.isLoading} hint="last 30 days" />
        <StatCard label="Minutes Used" value={minutes ?? "—"} icon="clock" accent="cyan" loading={overviewQ.isLoading} hint={estCost != null ? `~${formatMoney(estCost)} est. @ ₹${ASSUMED_RATE_PER_MIN}/min` : "last 30 days"} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Live agent status */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-900">Live Agent Status</h2>
            <span className="chip bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Running
            </span>
          </div>
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-slate-50 p-4">
            <div className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white">
              <Icon name="robot" className="h-6 w-6" />
              <span className="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-emerald-500 ring-2 ring-white" />
            </div>
            <div>
              <p className="font-semibold text-slate-800">Priya</p>
              <p className="text-xs text-slate-500">Ready to call · Hindi &amp; English</p>
            </div>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg border border-slate-100 p-3">
              <dt className="text-xs text-slate-400">Calls Today</dt>
              <dd className="text-lg font-bold text-slate-800">{s?.calls_today ?? 0}</dd>
            </div>
            <div className="rounded-lg border border-slate-100 p-3">
              <dt className="text-xs text-slate-400">Answered (mo.)</dt>
              <dd className="text-lg font-bold text-slate-800">{s?.answered_calls ?? 0}</dd>
            </div>
          </dl>
          <div className="mt-3 flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
            <span>Active calls · queue · worker health</span>
            <span className="font-semibold">Live telemetry soon</span>
          </div>
        </Card>

        {/* Recent activity */}
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 className="font-bold text-slate-900">Recent Activity</h2>
            <Link to="/calls/history" className="text-sm font-medium text-brand-600 hover:underline">
              View all calls
            </Link>
          </div>
          <div className="divide-y divide-slate-100">
            {loading && <div className="p-5 text-sm text-slate-400">Loading…</div>}
            {s && s.recent_calls.length === 0 && (
              <div className="p-8 text-center text-sm text-slate-500">
                No calls yet. Launch a campaign to put Priya to work.
              </div>
            )}
            {s?.recent_calls.map((c) => (
              <div key={c.id} className="flex items-center gap-3 px-5 py-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">
                  {initials(c.lead_name || c.phone_number)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-800">
                    {c.lead_name || c.phone_number || "Unknown"}
                  </p>
                  <p className="text-xs text-slate-400">
                    {titleCase(c.direction)} · {relativeTime(c.call_date)}
                  </p>
                </div>
                <ScorePill score={c.qualification_score} />
                <OutcomeBadge outcome={c.outcome} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Campaign performance */}
      <Card>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-bold text-slate-900">Campaign Performance</h2>
          <Link to="/campaigns" className="text-sm font-medium text-brand-600 hover:underline">
            All campaigns
          </Link>
        </div>
        <CampaignPerformance campaigns={campaignsQ.data?.items ?? []} loading={campaignsQ.isLoading} />
      </Card>
    </div>
  );
}

function CampaignPerformance({ campaigns, loading }: { campaigns: Campaign[]; loading: boolean }) {
  const analytics = useQueries({
    queries: campaigns.map((c) => ({
      queryKey: ["campaign-analytics", c.id],
      queryFn: () => api.get<CampaignAnalytics>(`/campaigns/${c.id}/analytics`),
    })),
  });

  if (loading) return <div className="p-5 text-sm text-slate-400">Loading…</div>;
  if (campaigns.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-sm text-slate-500">No campaigns yet.</p>
        <Link to="/campaigns/new" className="mt-3 inline-block">
          <Button size="sm"><Icon name="plus" className="h-4 w-4" /> Create your first campaign</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-100">
      {campaigns.map((c, i) => {
        const a = analytics[i]?.data;
        const pct = a && a.total_leads > 0 ? Math.round((a.attempted / a.total_leads) * 100) : 0;
        const conn = a && a.connected > 0 ? Math.round((a.connected / Math.max(1, a.attempted)) * 100) : 0;
        return (
          <Link key={c.id} to={`/campaigns/${c.id}`} className="block px-5 py-4 hover:bg-slate-50">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate font-semibold text-slate-800">{c.name}</p>
                  <CampaignStatusBadge status={c.status} />
                </div>
                <div className="mt-2 flex items-center gap-3">
                  <ProgressBar value={pct} tone={c.status === "running" ? "emerald" : "brand"} />
                  <span className="w-10 shrink-0 text-right text-xs font-medium text-slate-500">{pct}%</span>
                </div>
              </div>
              <div className="hidden gap-6 sm:flex">
                <Metric label="Connected" value={`${conn}%`} />
                <Metric label="Interested" value={a?.interested ?? "—"} />
                <Metric label="Site Visits" value={a?.site_visits ?? "—"} />
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="text-right">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-sm font-bold text-slate-800">{value}</p>
    </div>
  );
}
