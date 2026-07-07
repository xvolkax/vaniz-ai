import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { Icon, type IconName } from "./Icon";

export function ProgressBar({ value, tone = "brand" }: { value: number; tone?: string }) {
  const tones: Record<string, string> = {
    brand: "bg-brand-500",
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
  };
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div
        className={`h-full rounded-full ${tones[tone] || tones.brand} transition-all`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-100 ${className}`} />;
}

export function SubNav({ items }: { items: { to: string; label: string; end?: boolean }[] }) {
  return (
    <div className="mb-6 flex flex-wrap gap-1 border-b border-slate-200">
      {items.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          end={it.end}
          className={({ isActive }) =>
            `-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition ${
              isActive
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`
          }
        >
          {it.label}
        </NavLink>
      ))}
    </div>
  );
}

export function ComingSoon({
  icon,
  title,
  description,
  bullets,
}: {
  icon: IconName;
  title: string;
  description: string;
  bullets?: string[];
}) {
  return (
    <div className="card relative overflow-hidden p-10 text-center">
      <div className="pointer-events-none absolute inset-x-0 -top-24 mx-auto h-48 w-48 rounded-full bg-brand-500/10 blur-3xl" />
      <div className="relative">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-violet-500 text-white shadow-pop">
          <Icon name={icon} className="h-7 w-7" />
        </div>
        <h3 className="mt-5 text-xl font-bold text-slate-900">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">{description}</p>
        <span className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 ring-1 ring-amber-600/20">
          <Icon name="sparkles" className="h-3.5 w-3.5" /> Coming soon
        </span>
        {bullets && (
          <ul className="mx-auto mt-6 grid max-w-md gap-2 text-left">
            {bullets.map((b) => (
              <li key={b} className="flex items-center gap-2 text-sm text-slate-600">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                  <Icon name="check" className="h-3 w-3" />
                </span>
                {b}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function EmptyState({
  icon = "sparkles",
  title,
  hint,
  action,
}: {
  icon?: IconName;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white/60 p-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
        <Icon name={icon} className="h-6 w-6" />
      </div>
      <p className="mt-4 font-semibold text-slate-700">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
