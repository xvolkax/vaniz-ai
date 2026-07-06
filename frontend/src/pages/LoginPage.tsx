import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { api, setToken } from "@/lib/api";
import type { TokenResponse } from "@/lib/types";
import { Button, Input } from "@/components/ui/Primitives";
import { Spinner } from "@/components/ui/Spinner";

export function LoginPage() {
  const { isAuthenticated, ready, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({
    email: "",
    password: "",
    tenant_name: "",
    tenant_slug: "",
    full_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (ready && isAuthenticated) return <Navigate to="/" replace />;

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(form.email, form.password);
      } else {
        const res = await api.post<TokenResponse>("/auth/register", {
          tenant_name: form.tenant_name,
          tenant_slug: form.tenant_slug,
          email: form.email,
          password: form.password,
          full_name: form.full_name || null,
        });
        setToken(res.access_token);
        // Reload so AuthContext hydrates user + tenant from the new token.
        window.location.assign("/");
        return;
      }
      const from = (location.state as { from?: string })?.from || "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-xl font-bold text-white">
            P
          </div>
          <h1 className="text-xl font-semibold text-slate-900">
            Priya Broker Console
          </h1>
          <p className="text-sm text-slate-500">
            {mode === "login" ? "Sign in to your workspace" : "Create your organization"}
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          {mode === "register" && (
            <>
              <Input label="Organization name" value={form.tenant_name} onChange={set("tenant_name")} required />
              <Input label="Organization slug" value={form.tenant_slug} onChange={set("tenant_slug")} placeholder="acme-realty" required />
              <Input label="Your name" value={form.full_name} onChange={set("full_name")} />
            </>
          )}
          <Input label="Email" type="email" value={form.email} onChange={set("email")} required />
          <Input label="Password" type="password" value={form.password} onChange={set("password")} required minLength={mode === "register" ? 8 : undefined} />

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}

          <Button type="submit" disabled={busy} className="w-full">
            {busy && <Spinner className="h-4 w-4" />}
            {mode === "login" ? "Sign in" : "Create organization"}
          </Button>

          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? "New organization?" : "Already have an account?"}{" "}
            <button
              type="button"
              className="font-medium text-brand-600 hover:underline"
              onClick={() => {
                setError(null);
                setMode((m) => (m === "login" ? "register" : "login"));
              }}
            >
              {mode === "login" ? "Create one" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
