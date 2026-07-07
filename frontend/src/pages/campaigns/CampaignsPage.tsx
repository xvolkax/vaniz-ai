import { useState } from "react";
import { Link } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Campaign, CampaignAnalytics, Paginated } from "@/lib/types";
import { Card, PageHeader, Button } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState, ProgressBar, Skeleton } from "@/components/ui/Bits";
import { Pagination } from "@/components/ui/Pagination";
import { ErrorState } from "@/components/ui/States";
import { CampaignStatusBadge } from "@/components/StatusBadges";
import { formatDate } from "@/lib/format";

export const CAMPAIGNS_SUBNAV = [
  { to: "/campaigns", label: "Outbound Campaigns", end: true },
  { to: "/campaigns/lead-lists", label: "Lead Lists" },
  { to: "/campaigns/scheduled", label: "Scheduled Calls" },
];
const LIMIT = 12;

export function CampaignsPage() {
  const [offset, setOffset] = useState(0);
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["campaigns", offset],
    queryFn: () => api.get<Paginated<Campaign>>("/campaigns", { query: { limit: LIMIT, offset } }),
  });

  const analytics = useQueries({
    queries: (data?.items ?? []).map((c) => ({
      queryKey: ["campaign-analytics", c.id],
      queryFn: () => api.get<CampaignAnalytics>(`/campaigns/${c.id}/analytics`),
    })),
  });

  return (
    <div>
      <PageHeader
        title="Campaigns"
        subtitle="Launch AI calling campaigns and watch appointments roll in"
        actions={
          <Link to="/campaigns/new">
            <Button><Icon name="rocket" className="h-4 w-4" /> New Campaign</Button>
          </Link>
        }
      />
      <SubNav items={CAMPAIGNS_SUBNAV} />

      {isLoading && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-52 w-full rounded-2xl" />)}</div>}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState
          icon="rocket"
          title="No campaigns yet"
          hint="Create your first campaign — upload a lead list and let Priya start calling."
          action={<Link to="/campaigns/new"><Button><Icon name="plus" className="h-4 w-4" /> Create campaign</Button></Link>}
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((c, i) => {
              const a = analytics[i]?.data;
              const pct = a && a.total_leads > 0 ? Math.round((a.attempted / a.total_leads) * 100) : 0;
              const conv = a?.conversion_rate ?? 0;
              return (
                <Link key={c.id} to={`/campaigns/${c.id}`}>
                  <Card hover className="h-full p-5">
                    <div className="flex items-start justify-between">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white">
                        <Icon name="rocket" className="h-5 w-5" />
                      </div>
                      <CampaignStatusBadge status={c.status} />
                    </div>
                    <h3 className="mt-4 truncate text-lg font-bold text-slate-900">{c.name}</h3>
                    <p className="text-xs text-slate-400">Created {formatDate(c.created_at)}</p>

                    <div className="mt-4">
                      <div className="mb-1 flex justify-between text-xs text-slate-500">
                        <span>Progress</span><span className="font-semibold">{pct}%</span>
                      </div>
                      <ProgressBar value={pct} tone={c.status === "running" ? "emerald" : "brand"} />
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-2 border-t border-slate-100 pt-4 text-center">
                      <div><p className="text-xs text-slate-400">Leads</p><p className="font-bold text-slate-800">{a?.total_leads ?? "—"}</p></div>
                      <div><p className="text-xs text-slate-400">Interested</p><p className="font-bold text-emerald-600">{a?.interested ?? "—"}</p></div>
                      <div><p className="text-xs text-slate-400">Conv.</p><p className="font-bold text-brand-600">{conv}%</p></div>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
          <div className="mt-4"><Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} /></div>
        </>
      )}
    </div>
  );
}
