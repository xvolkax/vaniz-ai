import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

const accents: Record<string, string> = {
  brand: "from-brand-500 to-violet-500 text-white",
  emerald: "from-emerald-500 to-teal-500 text-white",
  amber: "from-amber-500 to-orange-500 text-white",
  rose: "from-rose-500 to-pink-500 text-white",
  slate: "from-slate-600 to-slate-500 text-white",
  cyan: "from-cyan-500 to-sky-500 text-white",
};

export function StatCard({
  label,
  value,
  icon,
  accent = "brand",
  delta,
  hint,
  loading = false,
}: {
  label: string;
  value: ReactNode;
  icon: IconName;
  accent?: keyof typeof accents;
  delta?: { value: string; up: boolean } | null;
  hint?: string;
  loading?: boolean;
}) {
  return (
    <div className="card card-hover p-5">
      <div className="flex items-start justify-between">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br shadow-sm ${accents[accent]}`}
        >
          <Icon name={icon} className="h-5 w-5" />
        </div>
        {delta && (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold ${
              delta.up ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"
            }`}
          >
            <Icon name={delta.up ? "arrow-up" : "arrow-down"} className="h-3 w-3" />
            {delta.value}
          </span>
        )}
      </div>
      <p className="mt-4 text-sm font-medium text-slate-500">{label}</p>
      {loading ? (
        <div className="mt-1 h-8 w-20 animate-pulse rounded-lg bg-slate-100" />
      ) : (
        <p className="mt-0.5 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      )}
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
