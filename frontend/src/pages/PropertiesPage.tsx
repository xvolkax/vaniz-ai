import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Property, PropertyType } from "@/lib/types";
import { Badge, Button, Card, Input, PageHeader, Select } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const TYPES: PropertyType[] = ["apartment", "villa", "plot", "commercial", "other"];

type Draft = Partial<Property> & { project_name: string; property_type: PropertyType };

export function PropertiesPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [activeOnly, setActiveOnly] = useState(false);
  const [editing, setEditing] = useState<Property | "new" | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["properties", activeOnly],
    queryFn: () =>
      api.get<Property[]>("/properties", {
        query: { active_only: activeOnly, limit: 200, offset: 0 },
      }),
  });

  const delMut = useMutation({
    mutationFn: (pid: string) => api.del(`/properties/${pid}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["properties"] }),
    onError: (e) => alert(e instanceof Error ? e.message : "Delete failed"),
  });

  return (
    <div>
      <PageHeader
        title="Properties"
        subtitle="Projects the AI offers on calls"
        actions={
          <>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
              Active only
            </label>
            {hasRole("agent") && <Button onClick={() => setEditing("new")}>New Property</Button>}
          </>
        }
      />

      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && data.length === 0 && (
        <EmptyState title="No properties" hint="Add your first project so the AI can pitch it." />
      )}
      {data && data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((p) => (
            <Card key={p.id} className="flex flex-col p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">{p.project_name}</h3>
                  <p className="text-sm text-slate-500">{p.location || "—"}</p>
                </div>
                <Badge tone={p.is_active ? "green" : "slate"}>
                  {p.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                <Badge tone="blue">{titleCase(p.property_type)}</Badge>
                {p.possession && <span>Possession: {p.possession}</span>}
              </div>
              {p.price && <p className="mt-2 text-sm text-slate-700">{p.price}</p>}
              {p.amenities.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">{p.amenities.join(", ")}</p>
              )}
              {hasRole("agent") && (
                <div className="mt-4 flex gap-2 border-t border-slate-100 pt-3">
                  <Button variant="secondary" onClick={() => setEditing(p)}>Edit</Button>
                  {hasRole("admin") && (
                    <Button variant="danger" onClick={() => confirm("Delete property?") && delMut.mutate(p.id)}>
                      Delete
                    </Button>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {editing && (
        <PropertyModal
          property={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function PropertyModal({ property, onClose }: { property: Property | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState<Draft>({
    project_name: property?.project_name || "",
    property_type: property?.property_type || "apartment",
    location: property?.location || "",
    price: property?.price || "",
    possession: property?.possession || "",
    carpet_area: property?.carpet_area || "",
    rera: property?.rera || "",
    is_active: property?.is_active ?? true,
  });

  const mut = useMutation({
    mutationFn: () => {
      const body = {
        project_name: form.project_name,
        property_type: form.property_type,
        location: form.location || null,
        price: form.price || null,
        possession: form.possession || null,
        carpet_area: form.carpet_area || null,
        rera: form.rera || null,
        is_active: form.is_active,
      };
      return property
        ? api.patch<Property>(`/properties/${property.id}`, body)
        : api.post<Property>("/properties", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["properties"] });
      onClose();
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "Save failed"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-lg p-6">
        <div onClick={(e) => e.stopPropagation()}>
          <h2 className="mb-4 text-lg font-semibold">{property ? "Edit" : "New"} Property</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input label="Project name" value={form.project_name} onChange={(e) => setForm({ ...form, project_name: e.target.value })} />
            <Select label="Type" value={form.property_type} onChange={(e) => setForm({ ...form, property_type: e.target.value as PropertyType })}>
              {TYPES.map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
            </Select>
            <Input label="Location" value={form.location || ""} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            <Input label="Price" value={form.price || ""} onChange={(e) => setForm({ ...form, price: e.target.value })} />
            <Input label="Possession" value={form.possession || ""} onChange={(e) => setForm({ ...form, possession: e.target.value })} />
            <Input label="Carpet area" value={form.carpet_area || ""} onChange={(e) => setForm({ ...form, carpet_area: e.target.value })} />
            <Input label="RERA" value={form.rera || ""} onChange={(e) => setForm({ ...form, rera: e.target.value })} />
            <label className="flex items-end gap-2 pb-2 text-sm text-slate-600">
              <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              Active
            </label>
          </div>
          {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button onClick={() => mut.mutate()} disabled={!form.project_name || mut.isPending}>Save</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
