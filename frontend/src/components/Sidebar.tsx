import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", end: true, icon: "M3 12l9-9 9 9M4 10v10h16V10" },
  { to: "/leads", label: "Leads", icon: "M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-4-4 4 4 0 004 4z" },
  { to: "/properties", label: "Properties", icon: "M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" },
  { to: "/calls", label: "Calls", icon: "M3 5a2 2 0 012-2h2l2 5-3 2a11 11 0 006 6l2-3 5 2v2a2 2 0 01-2 2A16 16 0 013 5z" },
  { to: "/campaigns", label: "Campaigns", icon: "M3 11l19-9-9 19-2-8-8-2z" },
  { to: "/appointments", label: "Appointments", icon: "M8 7V3m8 4V3M3 11h18M5 5h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z" },
  { to: "/analytics", label: "Analytics", icon: "M4 19V5m0 14h16M8 15v-4m4 4V9m4 6v-2" },
  { to: "/settings", label: "Settings", icon: "M10.3 3.3a2 2 0 013.4 0l.6 1a2 2 0 002.3 1l1.1-.3a2 2 0 012.4 2.4l-.3 1.1a2 2 0 001 2.3l1 .6a2 2 0 010 3.4l-1 .6a2 2 0 00-1 2.3l.3 1.1a2 2 0 01-2.4 2.4l-1.1-.3a2 2 0 00-2.3 1l-.6 1a2 2 0 01-3.4 0l-.6-1a2 2 0 00-2.3-1l-1.1.3a2 2 0 01-2.4-2.4l.3-1.1a2 2 0 00-1-2.3l-1-.6a2 2 0 010-3.4l1-.6a2 2 0 001-2.3l-.3-1.1A2 2 0 016.9 5l1.1.3a2 2 0 002.3-1l.6-1zM12 15a3 3 0 100-6 3 3 0 000 6z" },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex h-full flex-col gap-1 p-4">
      <div className="mb-4 flex items-center gap-2 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 font-bold text-white">
          P
        </div>
        <div>
          <p className="font-semibold leading-tight text-slate-900">Priya</p>
          <p className="text-xs text-slate-500">Broker Console</p>
        </div>
      </div>
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
              isActive
                ? "bg-brand-50 text-brand-700"
                : "text-slate-600 hover:bg-slate-100"
            }`
          }
        >
          <svg
            className="h-5 w-5 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d={item.icon} />
          </svg>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
