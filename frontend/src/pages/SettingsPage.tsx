import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsOverview, Tenant, User, UserRole } from "@/lib/types";
import { Card, PageHeader, Button, Input, Select, Badge } from "@/components/ui/Primitives";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Bits";
import { Modal } from "@/components/ui/Drawer";
import { ErrorState } from "@/components/ui/States";
import { titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const ROLES: UserRole[] = ["owner", "admin", "agent", "viewer"];
const TABS = [
  { key: "org", label: "Organization", icon: "settings" as IconName },
  { key: "phone", label: "Phone Numbers", icon: "phone" as IconName },
  { key: "integrations", label: "Integrations", icon: "bolt" as IconName },
  { key: "team", label: "Team", icon: "users" as IconName },
  { key: "billing", label: "Billing & Usage", icon: "chart" as IconName },
];

export function SettingsPage() {
  const [tab, setTab] = useState("org");
  return (
    <div>
      <PageHeader title="Settings" subtitle="Manage your workspace, team and integrations" />
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-2.5 whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${tab === t.key ? "bg-brand-50 text-brand-700" : "text-slate-500 hover:bg-slate-100"}`}>
              <Icon name={t.icon} className="h-4 w-4" /> {t.label}
            </button>
          ))}
        </nav>
        <div>
          {tab === "org" && <OrgTab />}
          {tab === "phone" && <PhoneTab />}
          {tab === "integrations" && <IntegrationsTab />}
          {tab === "team" && <TeamTab />}
          {tab === "billing" && <BillingTab />}
        </div>
      </div>
    </div>
  );
}

function OrgTab() {
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const editable = hasRole("admin");
  const { data, isLoading } = useQuery({ queryKey: ["tenant-me"], queryFn: () => api.get<Tenant>("/tenants/me") });
  const [form, setForm] = useState({ name: "", region: "", phone_number: "" });
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { if (data) setForm({ name: data.name || "", region: data.region || "", phone_number: data.phone_number || "" }); }, [data]);
  const save = useMutation({
    mutationFn: () => api.patch<Tenant>("/tenants/me", { name: form.name, region: form.region || null, phone_number: form.phone_number || null }),
    onSuccess: () => { setMsg("Saved"); qc.invalidateQueries({ queryKey: ["tenant-me"] }); setTimeout(() => setMsg(null), 2000); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "Failed"),
  });
  if (isLoading) return <Skeleton className="h-64 rounded-2xl" />;
  return (
    <Card className="p-6">
      <h2 className="mb-4 font-bold text-slate-900">Organization</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Company name" value={form.name} disabled={!editable} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Input label="Workspace slug" value={data?.slug || ""} disabled />
        <Input label="Region" value={form.region} disabled={!editable} onChange={(e) => setForm({ ...form, region: e.target.value })} />
        <Input label="Primary number" value={form.phone_number} disabled={!editable} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
      </div>
      {editable && <div className="mt-5 flex items-center gap-3"><Button onClick={() => save.mutate()} disabled={save.isPending}>Save changes</Button>{msg && <span className="text-sm text-slate-500">{msg}</span>}</div>}
    </Card>
  );
}

function PhoneTab() {
  const { data } = useQuery({ queryKey: ["tenant-me"], queryFn: () => api.get<Tenant>("/tenants/me") });
  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-slate-900">Your Numbers</h2>
          <Badge tone="green" dot>Connected</Badge>
        </div>
        <div className="mt-4 flex items-center gap-3 rounded-xl border border-slate-200 p-4">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600"><Icon name="phone" className="h-5 w-5" /></span>
          <div className="flex-1">
            <p className="font-semibold text-slate-800">{data?.phone_number || "No number set"}</p>
            <p className="text-xs text-slate-400">Inbound calls route to Priya · via LiveKit SIP</p>
          </div>
          <Badge tone="blue">Primary</Badge>
        </div>
      </Card>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="p-5"><h3 className="font-bold text-slate-900">SIP Trunk</h3><p className="mt-1 text-sm text-slate-500">Bring your own SIP provider (Vobiz, Twilio, Plivo).</p><Badge tone="amber">Self-serve setup coming soon</Badge></Card>
        <Card className="p-5"><h3 className="font-bold text-slate-900">Buy a Number</h3><p className="mt-1 text-sm text-slate-500">Provision new local numbers in one click.</p><Badge tone="amber">Coming soon</Badge></Card>
      </div>
    </div>
  );
}

function IntegrationsTab() {
  const items: { name: string; desc: string; icon: IconName; accent: string }[] = [
    { name: "Google Sheets", desc: "Auto-sync leads & results", icon: "list", accent: "from-emerald-500 to-teal-500" },
    { name: "HubSpot", desc: "Push qualified leads to your CRM", icon: "bolt", accent: "from-orange-500 to-amber-500" },
    { name: "Zoho CRM", desc: "Two-way lead sync", icon: "bolt", accent: "from-rose-500 to-pink-500" },
    { name: "Salesforce", desc: "Enterprise CRM sync", icon: "bolt", accent: "from-cyan-500 to-sky-500" },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((i) => (
        <Card key={i.name} className="flex items-center gap-4 p-5">
          <span className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${i.accent} text-white`}><Icon name={i.icon} className="h-6 w-6" /></span>
          <div className="flex-1">
            <h3 className="font-bold text-slate-900">{i.name}</h3>
            <p className="text-sm text-slate-500">{i.desc}</p>
          </div>
          <Button variant="secondary" size="sm" disabled>Connect</Button>
        </Card>
      ))}
    </div>
  );
}

function BillingTab() {
  const { data } = useQuery({ queryKey: ["analytics-overview", 30], queryFn: () => api.get<AnalyticsOverview>("/analytics/overview", { query: { days: 30 } }) });
  const minutes = data && data.avg_call_duration_seconds != null ? Math.round((data.total_calls * data.avg_call_duration_seconds) / 60) : 0;
  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="bg-gradient-to-br from-brand-600 to-violet-600 p-6 text-white">
          <p className="text-sm text-white/70">Current plan</p>
          <h2 className="text-2xl font-bold">Growth</h2>
          <p className="mt-1 text-sm text-white/80">Usage-based · billed monthly</p>
        </div>
        <div className="grid grid-cols-2 gap-4 p-6 sm:grid-cols-3">
          <div><p className="text-xs text-slate-400">Minutes (30d)</p><p className="text-2xl font-bold text-slate-900">{minutes}</p></div>
          <div><p className="text-xs text-slate-400">Calls (30d)</p><p className="text-2xl font-bold text-slate-900">{data?.total_calls ?? 0}</p></div>
          <div><p className="text-xs text-slate-400">Appointments (30d)</p><p className="text-2xl font-bold text-slate-900">{data?.site_visits ?? 0}</p></div>
        </div>
      </Card>
      <Card className="p-6">
        <h3 className="font-bold text-slate-900">Invoices &amp; payment</h3>
        <p className="mt-1 text-sm text-slate-500">Detailed billing, invoices and payment methods are coming soon.</p>
        <Badge tone="amber">Coming soon</Badge>
      </Card>
    </div>
  );
}

function TeamTab() {
  const qc = useQueryClient();
  const { hasRole, user } = useAuth();
  const { data, isLoading, isError, error, refetch } = useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/users") });
  const [showCreate, setShowCreate] = useState(false);
  const del = useMutation({ mutationFn: (id: string) => api.del(`/users/${id}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }), onError: (e) => alert(e instanceof Error ? e.message : "Failed") });
  const role = useMutation({ mutationFn: ({ id, r }: { id: string; r: UserRole }) => api.patch(`/users/${id}`, { role: r }), onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }), onError: (e) => alert(e instanceof Error ? e.message : "Failed") });

  if (!hasRole("admin")) return <Card className="p-8 text-center text-sm text-slate-500">Only admins can manage the team.</Card>;
  if (isLoading) return <Skeleton className="h-64 rounded-2xl" />;
  if (isError) return <ErrorState error={error} onRetry={refetch} />;

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h2 className="font-bold text-slate-900">Team Members</h2>
        <Button onClick={() => setShowCreate(true)}><Icon name="plus" className="h-4 w-4" /> Invite</Button>
      </div>
      <div className="divide-y divide-slate-100">
        {data!.map((u) => (
          <div key={u.id} className="flex items-center gap-3 px-5 py-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{(u.full_name || u.email)[0]?.toUpperCase()}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-slate-800">{u.full_name || "—"}</p>
              <p className="truncate text-xs text-slate-400">{u.email}</p>
            </div>
            <Badge tone={u.is_active ? "green" : "slate"}>{u.is_active ? "Active" : "Inactive"}</Badge>
            <Select value={u.role} disabled={u.id === user?.id || (u.role === "owner" && !hasRole("owner"))} onChange={(e) => role.mutate({ id: u.id, r: e.target.value as UserRole })} className="w-32">
              {ROLES.map((r) => <option key={r} value={r}>{titleCase(r)}</option>)}
            </Select>
            {u.id !== user?.id && <Button variant="ghost" size="sm" className="!text-rose-600" onClick={() => confirm(`Remove ${u.email}?`) && del.mutate(u.id)}>Remove</Button>}
          </div>
        ))}
      </div>
      {showCreate && <InviteModal onClose={() => setShowCreate(false)} />}
    </Card>
  );
}

function InviteModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "agent" as UserRole });
  const mut = useMutation({
    mutationFn: () => api.post<User>("/users", { email: form.email, password: form.password, full_name: form.full_name || null, role: form.role }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); onClose(); },
    onError: (e) => setErr(e instanceof Error ? e.message : "Failed"),
  });
  return (
    <Modal open onClose={onClose} title="Invite team member">
      <div className="space-y-3">
        <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Temporary password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} hint="At least 8 characters" />
        <Input label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <Select label="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
          {ROLES.map((r) => <option key={r} value={r}>{titleCase(r)}</option>)}
        </Select>
        {err && <p className="text-sm text-rose-600">{err}</p>}
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={() => mut.mutate()} disabled={!form.email || form.password.length < 8 || mut.isPending}>Send invite</Button>
      </div>
    </Modal>
  );
}
