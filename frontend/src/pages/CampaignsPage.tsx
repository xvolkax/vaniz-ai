import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Campaign, Paginated } from "@/lib/types";
import { Button, Card, Input, PageHeader } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { Pagination } from "@/components/ui/Pagination";
import { CampaignStatusBadge } from "@/components/StatusBadges";
import { formatDateTime } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const LIMIT = 20;

export function CampaignsPage() {
  const { hasRole } = useAuth();
  const [offset, setOffset] = useState(0);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["campaigns", offset],
    queryFn: () => api.get<Paginated<Campaign>>("/campaigns", { query: { limit: LIMIT, offset } }),
  });

  return (
    <div>
      <PageHeader
        title="Campaigns"
        subtitle={data ? `${data.total} total` : undefined}
        actions={hasRole("agent") ? <Button onClick={() => setShowCreate(true)}>New Campaign</Button> : undefined}
      />

      <Card>
        {isLoading && <LoadingBlock />}
        {isError && <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div>}
        {data && data.items.length === 0 && <div className="p-6"><EmptyState title="No campaigns yet" /></div>}
        {data && data.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Concurrency</th>
                    <th className="px-4 py-3">Working hours</th>
                    <th className="px-4 py-3">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <Link to={`/campaigns/${c.id}`} className="font-medium text-brand-700 hover:underline">
                          {c.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3"><CampaignStatusBadge status={c.status} /></td>
                      <td className="px-4 py-3 text-slate-600">{c.concurrency}</td>
                      <td className="px-4 py-3 text-slate-600">{c.working_hours_start}:00–{c.working_hours_end}:00</td>
                      <td className="px-4 py-3 text-slate-500">{formatDateTime(c.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>

      {showCreate && <CreateCampaignModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateCampaignModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    concurrency: 1,
    max_attempts: 3,
    retry_delay_minutes: 60,
    working_hours_start: 10,
    working_hours_end: 19,
  });

  const mut = useMutation({
    mutationFn: () => api.post<Campaign>("/campaigns", form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      onClose();
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "Failed"),
  });

  const num = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [k]: Number(e.target.value) });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-lg p-6">
        <div onClick={(e) => e.stopPropagation()}>
          <h2 className="mb-4 text-lg font-semibold">New Campaign</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <Input label="Concurrency" type="number" min={1} max={50} value={form.concurrency} onChange={num("concurrency")} />
            <Input label="Max attempts" type="number" min={1} max={10} value={form.max_attempts} onChange={num("max_attempts")} />
            <Input label="Retry delay (min)" type="number" min={1} value={form.retry_delay_minutes} onChange={num("retry_delay_minutes")} />
            <div className="grid grid-cols-2 gap-2">
              <Input label="Hours start" type="number" min={0} max={23} value={form.working_hours_start} onChange={num("working_hours_start")} />
              <Input label="Hours end" type="number" min={0} max={23} value={form.working_hours_end} onChange={num("working_hours_end")} />
            </div>
          </div>
          {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button onClick={() => mut.mutate()} disabled={!form.name || mut.isPending}>Create</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
