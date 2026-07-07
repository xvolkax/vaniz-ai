import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Tenant } from "@/lib/types";
import { Card, PageHeader, Button, Input, Select, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, Skeleton } from "@/components/ui/Bits";
import { AGENT_SUBNAV } from "./KnowledgeBasePage";
import { useAuth } from "@/auth/AuthContext";

export function AgentSettingsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const editable = hasRole("admin");
  const { data, isLoading } = useQuery({ queryKey: ["tenant-me"], queryFn: () => api.get<Tenant>("/tenants/me") });

  const [form, setForm] = useState({ builder_name: "", region: "", phone_number: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [cfg, setCfg] = useState({ language: "hi", voice: "priya", gender: "female", hours_start: "10", hours_end: "19", transfer: "", behaviour: "balanced" });

  useEffect(() => {
    if (data) setForm({ builder_name: data.builder_name || "", region: data.region || "", phone_number: data.phone_number || "" });
  }, [data]);

  const save = useMutation({
    mutationFn: () => api.patch<Tenant>("/tenants/me", { builder_name: form.builder_name || null, region: form.region || null, phone_number: form.phone_number || null }),
    onSuccess: () => { setMsg("Saved"); qc.invalidateQueries({ queryKey: ["tenant-me"] }); setTimeout(() => setMsg(null), 2000); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "Save failed"),
  });

  return (
    <div>
      <PageHeader title="Agent Settings" subtitle="Configure how Priya represents your business" />
      <SubNav items={AGENT_SUBNAV} />

      {isLoading ? <Skeleton className="h-64 rounded-2xl" /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Identity — persisted */}
          <Card className="p-6">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white"><Icon name="robot" className="h-5 w-5" /></span>
              <div>
                <h2 className="font-bold text-slate-900">Agent Identity</h2>
                <p className="text-xs text-slate-400">Saved to your workspace</p>
              </div>
            </div>
            <div className="space-y-4">
              <Input label="Speaks on behalf of" placeholder="Your company / builder name" value={form.builder_name} disabled={!editable} onChange={(e) => setForm({ ...form, builder_name: e.target.value })} />
              <Input label="Operating region" placeholder="Noida, Greater Noida" value={form.region} disabled={!editable} onChange={(e) => setForm({ ...form, region: e.target.value })} />
              <Input label="Inbound number (DID)" placeholder="+9198XXXXXXXX" value={form.phone_number} disabled={!editable} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} hint="Calls to this number route to Priya" />
            </div>
            {editable && (
              <div className="mt-5 flex items-center gap-3">
                <Button onClick={() => save.mutate()} disabled={save.isPending}>Save changes</Button>
                {msg && <span className="text-sm text-slate-500">{msg}</span>}
              </div>
            )}
          </Card>

          {/* Call configuration — UI ready */}
          <Card className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-sky-500 text-white"><Icon name="sliders" className="h-5 w-5" /></span>
                <div>
                  <h2 className="font-bold text-slate-900">Call Configuration</h2>
                  <p className="text-xs text-slate-400">Voice & behaviour defaults</p>
                </div>
              </div>
              <Badge tone="amber">Beta</Badge>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Select label="Language" value={cfg.language} onChange={(e) => setCfg({ ...cfg, language: e.target.value })}>
                <option value="hi">Hindi + English</option>
                <option value="en">English</option>
              </Select>
              <Select label="Voice" value={cfg.voice} onChange={(e) => setCfg({ ...cfg, voice: e.target.value })}>
                <option value="priya">Priya (warm)</option>
                <option value="neha">Neha (energetic)</option>
                <option value="arjun">Arjun (calm)</option>
              </Select>
              <Select label="Gender" value={cfg.gender} onChange={(e) => setCfg({ ...cfg, gender: e.target.value })}>
                <option value="female">Female</option>
                <option value="male">Male</option>
              </Select>
              <Select label="Behaviour" value={cfg.behaviour} onChange={(e) => setCfg({ ...cfg, behaviour: e.target.value })}>
                <option value="balanced">Balanced</option>
                <option value="assertive">Assertive</option>
                <option value="gentle">Gentle</option>
              </Select>
              <Input label="Business hours from" type="number" min={0} max={23} value={cfg.hours_start} onChange={(e) => setCfg({ ...cfg, hours_start: e.target.value })} />
              <Input label="Business hours to" type="number" min={0} max={23} value={cfg.hours_end} onChange={(e) => setCfg({ ...cfg, hours_end: e.target.value })} />
              <div className="col-span-2"><Input label="Human transfer number" placeholder="+9198XXXXXXXX" value={cfg.transfer} onChange={(e) => setCfg({ ...cfg, transfer: e.target.value })} hint="Priya warm-transfers hot leads here" /></div>
            </div>
            <div className="mt-5 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
              <Icon name="sparkles" className="h-4 w-4" /> Per-workspace voice &amp; behaviour persistence is rolling out shortly.
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
