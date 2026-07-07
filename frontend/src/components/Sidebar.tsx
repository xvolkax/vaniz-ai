import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Icon, type IconName } from "./ui/Icon";

interface NavChild {
  to: string;
  label: string;
}
interface NavItem {
  label: string;
  icon: IconName;
  to?: string;
  end?: boolean;
  children?: NavChild[];
}

const NAV: NavItem[] = [
  { label: "Dashboard", icon: "home", to: "/", end: true },
  {
    label: "Calls",
    icon: "phone",
    children: [
      { to: "/calls/live", label: "Live Calls" },
      { to: "/calls/history", label: "Call History" },
      { to: "/calls/recordings", label: "Recordings" },
      { to: "/calls/transcripts", label: "Transcripts" },
    ],
  },
  {
    label: "Campaigns",
    icon: "rocket",
    children: [
      { to: "/campaigns", label: "Outbound Campaigns" },
      { to: "/campaigns/lead-lists", label: "Lead Lists" },
      { to: "/campaigns/scheduled", label: "Scheduled Calls" },
    ],
  },
  {
    label: "AI Agent",
    icon: "robot",
    children: [
      { to: "/agent/settings", label: "Agent Settings" },
      { to: "/agent/prompt", label: "Prompt Builder" },
      { to: "/agent/knowledge", label: "Knowledge Base" },
      { to: "/agent/voice", label: "Voice Settings" },
      { to: "/agent/flows", label: "Call Flows" },
    ],
  },
  { label: "Appointments", icon: "calendar", to: "/appointments" },
  { label: "Leads", icon: "users", to: "/leads" },
  { label: "Analytics", icon: "chart", to: "/analytics" },
  { label: "Settings", icon: "settings", to: "/settings" },
];

function Group({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const location = useLocation();
  const groupActive = item.children?.some((c) => location.pathname.startsWith(c.to.split("?")[0]));
  const [open, setOpen] = useState<boolean>(!!groupActive);

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
          groupActive ? "text-slate-900" : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
        }`}
      >
        <Icon name={item.icon} className="h-5 w-5 shrink-0" />
        <span className="flex-1 text-left">{item.label}</span>
        <Icon name={open ? "chevron-down" : "chevron-right"} className="h-4 w-4 text-slate-400" />
      </button>
      {open && (
        <div className="ml-4 mt-0.5 space-y-0.5 border-l border-slate-200 pl-3">
          {item.children!.map((c) => (
            <NavLink
              key={c.to}
              to={c.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? "bg-brand-50 font-semibold text-brand-700"
                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                }`
              }
            >
              {c.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex h-full flex-col gap-0.5 overflow-y-auto p-4">
      <div className="mb-5 flex items-center gap-2.5 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-violet-500 font-bold text-white shadow-pop">
          P
        </div>
        <div>
          <p className="text-[15px] font-bold leading-tight text-slate-900">Priya AI</p>
          <p className="text-xs text-slate-400">Real-Estate Calling</p>
        </div>
      </div>

      {NAV.map((item) =>
        item.children ? (
          <Group key={item.label} item={item} onNavigate={onNavigate} />
        ) : (
          <NavLink
            key={item.label}
            to={item.to!}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                isActive
                  ? "bg-brand-50 text-brand-700 shadow-sm"
                  : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              }`
            }
          >
            <Icon name={item.icon} className="h-5 w-5 shrink-0" />
            {item.label}
          </NavLink>
        )
      )}

      <div className="mt-auto px-2 pt-6">
        <div className="rounded-2xl bg-gradient-to-br from-brand-600 to-violet-600 p-4 text-white shadow-pop">
          <p className="text-sm font-semibold">Priya is working 24/7</p>
          <p className="mt-1 text-xs text-white/80">
            Your AI agent calls, qualifies and books — while you close deals.
          </p>
        </div>
      </div>
    </nav>
  );
}
