import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return <div className={`card ${hover ? "card-hover" : ""} ${className}`}>{children}</div>;
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-[1.6rem] font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

type Variant = "primary" | "secondary" | "danger" | "ghost" | "success";
const variants: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white shadow-sm hover:bg-brand-700 focus:ring-brand-500/30",
  secondary:
    "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus:ring-slate-300/40",
  danger: "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500/30",
  success: "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500/30",
  ghost: "text-slate-600 hover:bg-slate-100 focus:ring-slate-300/40",
};
const sizes = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2.5 text-sm",
  lg: "px-5 py-3 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: keyof typeof sizes;
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Input({
  label,
  hint,
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string }) {
  return (
    <label className="block">
      {label && <span className="label">{label}</span>}
      <input className={`input ${className}`} {...rest} />
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}

export function Textarea({
  label,
  className = "",
  ...rest
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }) {
  return (
    <label className="block">
      {label && <span className="label">{label}</span>}
      <textarea className={`input min-h-[120px] resize-y ${className}`} {...rest} />
    </label>
  );
}

export function Select({
  label,
  className = "",
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string }) {
  return (
    <label className="block">
      {label && <span className="label">{label}</span>}
      <select className={`input appearance-none ${className}`} {...rest}>
        {children}
      </select>
    </label>
  );
}

export type Tone = "green" | "red" | "amber" | "blue" | "slate" | "purple" | "cyan";
const toneMap: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20",
  red: "bg-rose-50 text-rose-700 ring-1 ring-rose-600/20",
  amber: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
  blue: "bg-brand-50 text-brand-700 ring-1 ring-brand-600/20",
  slate: "bg-slate-100 text-slate-600 ring-1 ring-slate-500/15",
  purple: "bg-purple-50 text-purple-700 ring-1 ring-purple-600/20",
  cyan: "bg-cyan-50 text-cyan-700 ring-1 ring-cyan-600/20",
};

export function Badge({
  children,
  tone = "slate",
  dot = false,
}: {
  children: ReactNode;
  tone?: Tone;
  dot?: boolean;
}) {
  return (
    <span className={`chip ${toneMap[tone]}`}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
