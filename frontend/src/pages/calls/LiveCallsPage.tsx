import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallListItem, Paginated } from "@/lib/types";
import { Card, PageHeader, Button, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState } from "@/components/ui/Bits";
import { CALLS_SUBNAV } from "./CallHistoryPage";
import { formatDuration, titleCase } from "@/lib/format";

// A call is "live" if it has started but not ended and has no final outcome yet.
export function LiveCallsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["calls-live"],
    queryFn: () => api.get<Paginated<CallListItem>>("/calls", { query: { limit: 25, offset: 0 } }),
    refetchInterval: 5000,
  });

  const live = (data?.items ?? []).filter((c) => !c.outcome && !c.duration_seconds);

  return (
    <div>
      <PageHeader
        title="Live Calls"
        subtitle="Calls Priya is handling right now"
        actions={<Badge tone="green" dot>Auto-refreshing</Badge>}
      />
      <SubNav items={CALLS_SUBNAV} />

      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-400">Checking for active calls…</Card>
      ) : live.length === 0 ? (
        <EmptyState
          icon="phone-live"
          title="No live calls right now"
          hint="When a campaign is running, active conversations appear here in real time — with listen, whisper and take-over controls."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {live.map((c) => (
            <Card key={c.id} className="p-5">
              <div className="flex items-center gap-3">
                <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white">
                  <Icon name="phone-live" className="h-5 w-5" />
                  <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-xl bg-emerald-400/60" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold text-slate-900">{c.lead_name || c.phone_number}</p>
                  <p className="text-xs text-slate-400">{c.phone_number} · {titleCase(c.direction)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400">Duration</p>
                  <p className="font-semibold text-slate-700">{formatDuration(c.duration_seconds) || "live"}</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-4 gap-2">
                {(["play", "wave", "users", "x"] as const).map((ic, idx) => (
                  <button
                    key={ic}
                    disabled
                    title="Real-time controls coming soon"
                    className="flex flex-col items-center gap-1 rounded-xl border border-slate-200 py-2 text-xs text-slate-400"
                  >
                    <Icon name={ic} className="h-4 w-4" />
                    {["Listen", "Whisper", "Take Over", "End"][idx]}
                  </button>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
        <Icon name="sparkles" className="h-4 w-4" />
        Live monitoring controls (listen / whisper / take-over) are on the roadmap.
        <Button size="sm" variant="ghost" className="!text-amber-700">Learn more</Button>
      </div>
    </div>
  );
}
