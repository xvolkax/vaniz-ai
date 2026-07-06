import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Tenant, User, UserRole } from "@/lib/types";
import { Badge, Button, Card, Input, PageHeader, Select } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import { titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

const ROLES: UserRole[] = ["owner", "admin", "agent", "viewer"];

export function SettingsPage() {
  const { user, hasRole } = useAuth();
  return (
    <div>
      <PageHeader title="Settings" subtitle="Profile, organization & team" />
      <div className="space-y-6">
        <ProfileCard />
        <TenantCard editable={hasRole("admin")} />
        {hasRole("admin") && <UsersCard currentUserId={user?.id} />}
      </div>
    </div>
  );
}

function ProfileCard() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <Card className="p-5">
      <h2 className="mb-4 font-semibold text-slate-800">Your Profile</h2>
      <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
        <div><p className="text-xs uppercase text-slate-400">Name</p><p>{user.full_name || "—"}</p></div>
        <div><p className="text-xs uppercase text-slate-400">Email</p><p>{user.email}</p></div>
        <div><p className="text-xs uppercase text-slate-400">Role</p><p><Badge tone="blue">{titleCase(user.role)}</Badge></p></div>
        <div><p className="text-xs uppercase text-slate-400">Status</p><p>{user.is_active ? "Active" : "Inactive"}</p></div>
      </div>
    </Card>
  );
}

function TenantCard({ editable }: { editable: boolean }) {
  const qc = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => api.get<Tenant>("/tenants/me"),
  });
  const [form, setForm] = useState({ name: "", phone_number: "", builder_name: "", region: "" });
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name || "",
        phone_number: data.phone_number || "",
        builder_name: data.builder_name || "",
        region: data.region || "",
      });
    }
  }, [data]);

  const mut = useMutation({
    mutationFn: () =>
      api.patch<Tenant>("/tenants/me", {
        name: form.name,
        phone_number: form.phone_number || null,
        builder_name: form.builder_name || null,
        region: form.region || null,
      }),
    onSuccess: () => {
      setMsg("Saved.");
      qc.invalidateQueries({ queryKey: ["tenant-me"] });
      setTimeout(() => setMsg(null), 2000);
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : "Save failed"),
  });

  return (
    <Card className="p-5">
      <h2 className="mb-4 font-semibold text-slate-800">Organization</h2>
      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input label="Name" value={form.name} disabled={!editable} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input label="Slug" value={data.slug} disabled />
            <Input label="Inbound number" value={form.phone_number} disabled={!editable} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
            <Input label="Builder name" value={form.builder_name} disabled={!editable} onChange={(e) => setForm({ ...form, builder_name: e.target.value })} />
            <Input label="Region" value={form.region} disabled={!editable} onChange={(e) => setForm({ ...form, region: e.target.value })} />
          </div>
          {editable && (
            <div className="mt-4 flex items-center gap-3">
              <Button onClick={() => mut.mutate()} disabled={mut.isPending}>Save changes</Button>
              {msg && <span className="text-sm text-slate-500">{msg}</span>}
            </div>
          )}
        </>
      )}
    </Card>
  );
}

function UsersCard({ currentUserId }: { currentUserId?: string }) {
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });
  const [showCreate, setShowCreate] = useState(false);

  const delMut = useMutation({
    mutationFn: (uid: string) => api.del(`/users/${uid}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e) => alert(e instanceof Error ? e.message : "Delete failed"),
  });
  const roleMut = useMutation({
    mutationFn: ({ uid, role }: { uid: string; role: UserRole }) => api.patch(`/users/${uid}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e) => alert(e instanceof Error ? e.message : "Update failed"),
  });

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h2 className="font-semibold text-slate-800">Team</h2>
        <Button onClick={() => setShowCreate(true)}>Invite user</Button>
      </div>
      {isLoading && <LoadingBlock />}
      {isError && <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div>}
      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((u) => (
                <tr key={u.id}>
                  <td className="px-5 py-3">{u.full_name || "—"}</td>
                  <td className="px-5 py-3 text-slate-600">{u.email}</td>
                  <td className="px-5 py-3">
                    <Select
                      value={u.role}
                      disabled={u.id === currentUserId || (u.role === "owner" && !hasRole("owner"))}
                      onChange={(e) => roleMut.mutate({ uid: u.id, role: e.target.value as UserRole })}
                      className="w-32"
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{titleCase(r)}</option>)}
                    </Select>
                  </td>
                  <td className="px-5 py-3">
                    <Badge tone={u.is_active ? "green" : "slate"}>{u.is_active ? "Active" : "Inactive"}</Badge>
                  </td>
                  <td className="px-5 py-3 text-right">
                    {u.id !== currentUserId && (
                      <Button variant="danger" onClick={() => confirm(`Delete ${u.email}?`) && delMut.mutate(u.id)}>
                        Delete
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} />}
    </Card>
  );
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "agent" as UserRole });

  const mut = useMutation({
    mutationFn: () =>
      api.post<User>("/users", {
        email: form.email,
        password: form.password,
        full_name: form.full_name || null,
        role: form.role,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "Failed"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-md p-6">
        <div onClick={(e) => e.stopPropagation()}>
          <h2 className="mb-4 text-lg font-semibold">Invite User</h2>
          <div className="space-y-3">
            <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Input label="Temporary password" type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} minLength={8} />
            <Input label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            <Select label="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
              {ROLES.map((r) => <option key={r} value={r}>{titleCase(r)}</option>)}
            </Select>
            {err && <p className="text-sm text-red-600">{err}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button onClick={() => mut.mutate()} disabled={!form.email || form.password.length < 8 || mut.isPending}>Create</Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
