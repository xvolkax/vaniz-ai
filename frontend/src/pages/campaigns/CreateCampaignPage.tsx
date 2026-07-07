import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Campaign, Lead, LeadImportResult, Paginated } from "@/lib/types";
import { Card, PageHeader, Button, Input } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Bits";
import { titleCase } from "@/lib/format";

const STEPS = ["Details", "Leads", "Schedule", "Launch"];
const GOALS = ["Site visit booking", "Lead qualification", "Re-engagement", "Cold outreach"];

export function CreateCampaignPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [goal, setGoal] = useState(GOALS[0]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [leadSearch, setLeadSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [cfg, setCfg] = useState({
    concurrency: 3,
    max_attempts: 3,
    retry_delay_minutes: 60,
    working_hours_start: 10,
    working_hours_end: 19,
  });

  const leadsQ = useQuery({
    queryKey: ["leads-picker", appliedSearch],
    queryFn: () =>
      api.get<Paginated<Lead>>("/leads", {
        query: { search: appliedSearch || undefined, limit: 100, offset: 0, sort_by: "created_at", order: "desc" },
      }),
    enabled: step === 1,
  });

  const importMut = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.upload<LeadImportResult>("/leads/import", fd);
    },
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["leads-picker"] });
      alert(`Imported ${r.created} new + ${r.updated} updated lead(s). Select them below.`);
    },
    onError: (e) => alert(e instanceof Error ? e.message : "Import failed"),
  });

  const launchMut = useMutation({
    mutationFn: async () => {
      const campaign = await api.post<Campaign>("/campaigns", {
        name,
        ...cfg,
        lead_ids: Array.from(selected),
      });
      await api.post(`/campaigns/${campaign.id}/start`);
      return campaign;
    },
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      navigate(`/campaigns/${c.id}`);
    },
    onError: (e) => setError(e instanceof Error ? e.message : "Failed to launch"),
  });

  const num = (k: keyof typeof cfg) => (e: { target: { value: string } }) =>
    setCfg({ ...cfg, [k]: Number(e.target.value) });

  function toggle(id: string) {
    setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  const canNext =
    (step === 0 && name.trim().length > 1) ||
    (step === 1 && selected.size > 0) ||
    step === 2;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="New Campaign"
        subtitle="Four quick steps to put Priya to work"
        actions={<Button variant="ghost" onClick={() => navigate("/campaigns")}>Cancel</Button>}
      />

      {/* Stepper */}
      <div className="mb-6 flex items-center">
        {STEPS.map((label, i) => (
          <div key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex items-center gap-2">
              <span className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                i < step ? "bg-emerald-500 text-white" : i === step ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-500"
              }`}>
                {i < step ? <Icon name="check" className="h-4 w-4" /> : i + 1}
              </span>
              <span className={`hidden text-sm font-medium sm:block ${i === step ? "text-slate-900" : "text-slate-400"}`}>{label}</span>
            </div>
            {i < STEPS.length - 1 && <div className={`mx-3 h-0.5 flex-1 ${i < step ? "bg-emerald-500" : "bg-slate-200"}`} />}
          </div>
        ))}
      </div>

      <Card className="p-6">
        {step === 0 && (
          <div className="space-y-5">
            <Input label="Campaign name" placeholder="e.g. Diwali Site-Visit Drive" value={name} onChange={(e) => setName(e.target.value)} />
            <div>
              <span className="label">Campaign goal</span>
              <div className="grid grid-cols-2 gap-3">
                {GOALS.map((g) => (
                  <button
                    key={g}
                    onClick={() => setGoal(g)}
                    className={`rounded-xl border p-3 text-left text-sm font-medium transition ${
                      goal === g ? "border-brand-500 bg-brand-50 text-brand-700 ring-4 ring-brand-500/10" : "border-slate-200 text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div>
            <div className="mb-3 flex items-center justify-between gap-3">
              <form onSubmit={(e) => { e.preventDefault(); setAppliedSearch(leadSearch); }} className="relative flex-1">
                <Icon name="search" className="pointer-events-none absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
                <Input className="!pl-10" placeholder="Search leads…" value={leadSearch} onChange={(e) => setLeadSearch(e.target.value)} />
              </form>
              <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) importMut.mutate(f); e.target.value = ""; }} />
              <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={importMut.isPending}>
                <Icon name="upload" className="h-4 w-4" /> Import CSV
              </Button>
            </div>

            <div className="max-h-80 overflow-y-auto rounded-xl border border-slate-200">
              {leadsQ.isLoading ? (
                <div className="space-y-2 p-3">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
              ) : (leadsQ.data?.items.length ?? 0) === 0 ? (
                <div className="p-8 text-center text-sm text-slate-500">No leads. Import a CSV to get started.</div>
              ) : (
                leadsQ.data!.items.map((l) => (
                  <label key={l.id} className="flex cursor-pointer items-center gap-3 border-b border-slate-100 px-4 py-2.5 text-sm last:border-0 hover:bg-slate-50">
                    <input type="checkbox" checked={selected.has(l.id)} onChange={() => toggle(l.id)} className="h-4 w-4 rounded border-slate-300 text-brand-600" />
                    <span className="font-medium text-slate-800">{l.name || "Unnamed"}</span>
                    <span className="text-slate-400">{l.phone_number}</span>
                    <span className="ml-auto text-xs text-slate-400">{titleCase(l.source)}</span>
                  </label>
                ))
              )}
            </div>
            <p className="mt-2 text-sm text-slate-500">{selected.size} lead(s) selected</p>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <Input label="Concurrent calls" type="number" min={1} max={50} value={cfg.concurrency} onChange={num("concurrency")} hint="How many leads Priya calls at once" />
              <Input label="Retry attempts" type="number" min={1} max={10} value={cfg.max_attempts} onChange={num("max_attempts")} hint="Tries if no answer" />
            </div>
            <Input label="Retry delay (minutes)" type="number" min={1} value={cfg.retry_delay_minutes} onChange={num("retry_delay_minutes")} hint="Wait before retrying a lead" />
            <div>
              <span className="label">Business hours (IST)</span>
              <div className="grid grid-cols-2 gap-4">
                <Input type="number" min={0} max={23} value={cfg.working_hours_start} onChange={num("working_hours_start")} hint="Start hour" />
                <Input type="number" min={0} max={23} value={cfg.working_hours_end} onChange={num("working_hours_end")} hint="End hour" />
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="rounded-2xl bg-gradient-to-br from-brand-600 to-violet-600 p-5 text-white">
              <p className="text-sm text-white/70">Ready to launch</p>
              <h3 className="text-xl font-bold">{name}</h3>
              <p className="mt-1 text-sm text-white/80">{goal}</p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Review label="Leads" value={`${selected.size} selected`} />
              <Review label="Concurrent calls" value={String(cfg.concurrency)} />
              <Review label="Retry attempts" value={String(cfg.max_attempts)} />
              <Review label="Retry delay" value={`${cfg.retry_delay_minutes} min`} />
              <Review label="Business hours" value={`${cfg.working_hours_start}:00 – ${cfg.working_hours_end}:00 IST`} />
            </div>
            {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
          </div>
        )}

        <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-5">
          <Button variant="ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>Back</Button>
          {step < 3 ? (
            <Button disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
              Continue <Icon name="chevron-right" className="h-4 w-4" />
            </Button>
          ) : (
            <Button variant="success" disabled={launchMut.isPending || selected.size === 0} onClick={() => launchMut.mutate()}>
              <Icon name="rocket" className="h-4 w-4" /> {launchMut.isPending ? "Launching…" : "Launch Campaign"}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

function Review({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="font-semibold text-slate-800">{value}</p>
    </div>
  );
}
