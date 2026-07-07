import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Property, PropertyType } from "@/lib/types";
import { Card, PageHeader, Button, Input, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState, Skeleton } from "@/components/ui/Bits";
import { Modal } from "@/components/ui/Drawer";
import { ErrorState } from "@/components/ui/States";
import { titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

export const AGENT_SUBNAV = [
  { to: "/agent/settings", label: "Agent Settings" },
  { to: "/agent/prompt", label: "Prompt Builder" },
  { to: "/agent/knowledge", label: "Knowledge Base" },
  { to: "/agent/voice", label: "Voice Settings" },
  { to: "/agent/flows", label: "Call Flows" },
];

const TYPES: PropertyType[] = ["apartment", "villa", "plot", "commercial", "other"];

export function KnowledgeBasePage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Property | "new" | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["properties"],
    queryFn: () => api.get<Property[]>("/properties", { query: { limit: 200, offset: 0 } }),
  });

  const del = useMutation({
    mutationFn: (pid: string) => api.del(`/properties/${pid}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["properties"] }),
    onError: (e) => alert(e instanceof Error ? e.message : "Delete failed"),
  });

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle="Projects Priya knows about — she uses these details live on every call"
        actions={hasRole("agent") ? <Button onClick={() => setEditing("new")}><Icon name="plus" className="h-4 w-4" /> Add Project</Button> : undefined}
      />
      <SubNav items={AGENT_SUBNAV} />

      <div className="mb-4 flex items-center gap-3 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
        <Icon name="sparkles" className="h-5 w-5 shrink-0" />
        No coding or YAML — just fill in the details. Priya automatically references them when leads ask about price, location, possession or amenities.
      </div>

      {isLoading && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-56 rounded-2xl" />)}</div>}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && data.length === 0 && (
        <EmptyState icon="book" title="No projects yet" hint="Add your first project so Priya can pitch it to leads." action={<Button onClick={() => setEditing("new")}><Icon name="plus" className="h-4 w-4" /> Add Project</Button>} />
      )}

      {data && data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((p) => (
            <Card key={p.id} hover className="flex flex-col p-5">
              <div className="flex items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white">
                  <Icon name="home" className="h-5 w-5" />
                </div>
                <Badge tone={p.is_active ? "green" : "slate"} dot>{p.is_active ? "Live" : "Hidden"}</Badge>
              </div>
              <h3 className="mt-4 font-bold text-slate-900">{p.project_name}</h3>
              <p className="text-sm text-slate-500">{p.location || "—"}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge tone="blue">{titleCase(p.property_type)}</Badge>
                {p.possession && <Badge tone="cyan">{p.possession}</Badge>}
              </div>
              {p.price && <p className="mt-3 text-sm font-semibold text-slate-700">{p.price}</p>}
              {p.amenities.length > 0 && (
                <p className="mt-2 line-clamp-2 text-xs text-slate-400">{p.amenities.join(" · ")}</p>
              )}
              {hasRole("agent") && (
                <div className="mt-auto flex gap-2 border-t border-slate-100 pt-4">
                  <Button variant="secondary" size="sm" className="flex-1" onClick={() => setEditing(p)}>Edit</Button>
                  {hasRole("admin") && <Button variant="ghost" size="sm" className="!text-rose-600" onClick={() => confirm("Delete project?") && del.mutate(p.id)}>Delete</Button>}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {editing && <ProjectModal property={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function ProjectModal({ property, onClose }: { property: Property | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [amenityInput, setAmenityInput] = useState("");
  const [form, setForm] = useState({
    project_name: property?.project_name || "",
    property_type: property?.property_type || ("apartment" as PropertyType),
    location: property?.location || "",
    price: property?.price || "",
    possession: property?.possession || "",
    carpet_area: property?.carpet_area || "",
    rera: property?.rera || "",
    amenities: property?.amenities || [],
    is_active: property?.is_active ?? true,
  });

  const mut = useMutation({
    mutationFn: () => {
      const body = { ...form, location: form.location || null, price: form.price || null, possession: form.possession || null, carpet_area: form.carpet_area || null, rera: form.rera || null };
      return property ? api.patch<Property>(`/properties/${property.id}`, body) : api.post<Property>("/properties", body);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["properties"] }); onClose(); },
    onError: (e) => setErr(e instanceof Error ? e.message : "Save failed"),
  });

  function addAmenity() {
    const v = amenityInput.trim();
    if (v && !form.amenities.includes(v)) setForm({ ...form, amenities: [...form.amenities, v] });
    setAmenityInput("");
  }

  return (
    <Modal open onClose={onClose} title={property ? "Edit project" : "Add project"} width="max-w-2xl">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><Input label="Project name" placeholder="Green Valley" value={form.project_name} onChange={(e) => setForm({ ...form, project_name: e.target.value })} /></div>
        <label className="block">
          <span className="label">Property type</span>
          <select className="input appearance-none" value={form.property_type} onChange={(e) => setForm({ ...form, property_type: e.target.value as PropertyType })}>
            {TYPES.map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
          </select>
        </label>
        <Input label="Location" placeholder="Noida Extension" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        <Input label="Price" placeholder="45 Lakhs" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
        <Input label="Possession" placeholder="Dec 2027" value={form.possession} onChange={(e) => setForm({ ...form, possession: e.target.value })} />
        <Input label="Carpet area" placeholder="1150 sq ft" value={form.carpet_area} onChange={(e) => setForm({ ...form, carpet_area: e.target.value })} />
        <Input label="RERA" placeholder="UPRERAPRJ..." value={form.rera} onChange={(e) => setForm({ ...form, rera: e.target.value })} />
        <div className="sm:col-span-2">
          <span className="label">Amenities</span>
          <div className="flex gap-2">
            <input className="input" placeholder="Pool, Gym, Clubhouse…" value={amenityInput}
              onChange={(e) => setAmenityInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addAmenity(); } }} />
            <Button type="button" variant="secondary" onClick={addAmenity}>Add</Button>
          </div>
          {form.amenities.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {form.amenities.map((a) => (
                <span key={a} className="chip bg-slate-100 text-slate-600">
                  {a}
                  <button onClick={() => setForm({ ...form, amenities: form.amenities.filter((x) => x !== a) })} className="ml-1 text-slate-400 hover:text-rose-500">
                    <Icon name="x" className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600 sm:col-span-2">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-brand-600" />
          Live — Priya can pitch this project on calls
        </label>
      </div>
      {err && <p className="mt-3 text-sm text-rose-600">{err}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={() => mut.mutate()} disabled={!form.project_name || mut.isPending}>Save project</Button>
      </div>
    </Modal>
  );
}
