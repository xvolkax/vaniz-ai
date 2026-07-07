import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Lead, LeadSource, Paginated } from "@/lib/types";
import { Card, PageHeader, Button } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav } from "@/components/ui/Bits";
import { CAMPAIGNS_SUBNAV } from "./CampaignsPage";
import { titleCase } from "@/lib/format";

const SOURCES: { key: LeadSource; label: string; accent: string }[] = [
  { key: "csv_import", label: "CSV Imports", accent: "from-brand-500 to-violet-500" },
  { key: "manual", label: "Manually Added", accent: "from-emerald-500 to-teal-500" },
  { key: "inbound_call", label: "Inbound Callers", accent: "from-cyan-500 to-sky-500" },
  { key: "outbound_call", label: "Outbound Reached", accent: "from-amber-500 to-orange-500" },
  { key: "api", label: "API / Integrations", accent: "from-purple-500 to-fuchsia-500" },
  { key: "other", label: "Other", accent: "from-slate-500 to-slate-600" },
];

export function LeadListsPage() {
  const counts = useQueries({
    queries: SOURCES.map((s) => ({
      queryKey: ["lead-count", s.key],
      queryFn: () => api.get<Paginated<Lead>>("/leads", { query: { source: s.key, limit: 1, offset: 0 } }),
    })),
  });

  return (
    <div>
      <PageHeader
        title="Lead Lists"
        subtitle="Your leads grouped by where they came from"
        actions={<Link to="/leads"><Button variant="secondary"><Icon name="upload" className="h-4 w-4" /> Import leads</Button></Link>}
      />
      <SubNav items={CAMPAIGNS_SUBNAV} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SOURCES.map((s, i) => {
          const total = counts[i]?.data?.total ?? 0;
          const loading = counts[i]?.isLoading;
          return (
            <Card key={s.key} hover className="p-5">
              <div className="flex items-center justify-between">
                <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${s.accent} text-white`}>
                  <Icon name="list" className="h-5 w-5" />
                </div>
                <span className="text-2xl font-bold text-slate-900">{loading ? "…" : total}</span>
              </div>
              <h3 className="mt-4 font-bold text-slate-900">{s.label}</h3>
              <p className="text-xs text-slate-400">{titleCase(s.key)} · {total} lead{total === 1 ? "" : "s"}</p>
              <div className="mt-4 flex gap-2">
                <Link to={`/leads?source=${s.key}`} className="flex-1">
                  <Button variant="secondary" size="sm" className="w-full">View</Button>
                </Link>
                <Link to="/campaigns/new" className="flex-1">
                  <Button size="sm" className="w-full"><Icon name="rocket" className="h-4 w-4" /> Call</Button>
                </Link>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
