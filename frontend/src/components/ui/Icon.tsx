// Lightweight inline icon set (stroke-based, 24x24) — no icon dependency.
export type IconName =
  | "home"
  | "phone"
  | "phone-live"
  | "history"
  | "recording"
  | "transcript"
  | "rocket"
  | "list"
  | "clock"
  | "robot"
  | "sliders"
  | "sparkles"
  | "book"
  | "wave"
  | "flow"
  | "calendar"
  | "users"
  | "chart"
  | "settings"
  | "chevron-down"
  | "chevron-right"
  | "menu"
  | "search"
  | "bell"
  | "plus"
  | "upload"
  | "download"
  | "play"
  | "check"
  | "x"
  | "arrow-up"
  | "arrow-down"
  | "phone-incoming"
  | "phone-outgoing"
  | "target"
  | "bolt"
  | "logout";

const PATHS: Record<IconName, string> = {
  home: "M3 11.5 12 4l9 7.5M5 10v10h14V10",
  phone: "M3 5a2 2 0 0 1 2-2h2l2 5-3 2a11 11 0 0 0 6 6l2-3 5 2v2a2 2 0 0 1-2 2A16 16 0 0 1 3 5z",
  "phone-live":
    "M3 5a2 2 0 0 1 2-2h2l2 5-3 2a11 11 0 0 0 6 6l2-3 5 2v2a2 2 0 0 1-2 2A16 16 0 0 1 3 5z",
  history: "M3 12a9 9 0 1 0 3-6.7M3 4v4h4M12 8v4l3 2",
  recording: "M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zM5 11a7 7 0 0 0 14 0M12 18v3",
  transcript: "M4 6h16M4 10h16M4 14h10M4 18h7",
  rocket:
    "M5 15c-1.5 1-2 4-2 4s3-.5 4-2m3-2 5-5a7 7 0 0 0 2-5 7 7 0 0 0-5 2l-5 5m3 3-3-3m6 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  clock: "M12 8v4l3 2M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z",
  robot: "M12 3v3M8 9h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2zM9 14h.01M15 14h.01",
  sliders: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
  sparkles: "M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3zM19 14l.9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14z",
  book: "M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2V5zM18 3v16",
  wave: "M3 12h2l2-6 3 12 3-9 2 3h6",
  flow: "M6 4h4v4H6zM14 16h4v4h-4zM8 8v4a2 2 0 0 0 2 2h4M16 8h.01",
  calendar: "M8 7V3m8 4V3M3 11h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z",
  users: "M17 20h5v-2a4 4 0 0 0-3-3.87M9 20H4v-2a4 4 0 0 1 3-3.87M13 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4z",
  chart: "M4 19V5M4 19h16M8 16v-4m4 4V8m4 8v-6",
  settings:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 13a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 6.8 19l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0-1.2-2.9H2a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4 6.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 2.9-1.2V2a2 2 0 1 1 4 0v.1A1.7 1.7 0 0 0 17.2 4l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0 1.2 2.9H22a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  "chevron-down": "M6 9l6 6 6-6",
  "chevron-right": "M9 6l6 6-6 6",
  menu: "M4 6h16M4 12h16M4 18h16",
  search: "M21 21l-4.3-4.3M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14z",
  bell: "M15 17h5l-1.4-1.4A2 2 0 0 1 18 14V11a6 6 0 1 0-12 0v3a2 2 0 0 1-.6 1.6L4 17h5m6 0v1a3 3 0 1 1-6 0v-1",
  plus: "M12 5v14M5 12h14",
  upload: "M12 15V3m0 0L8 7m4-4 4 4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2",
  download: "M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2",
  play: "M6 4l14 8-14 8z",
  check: "M5 13l4 4L19 7",
  x: "M6 6l12 12M18 6L6 18",
  "arrow-up": "M12 19V5m0 0l-6 6m6-6l6 6",
  "arrow-down": "M12 5v14m0 0l6-6m-6 6l-6-6",
  "phone-incoming": "M16 2v6h6M22 2l-8 8M3 5a2 2 0 0 1 2-2h2l2 5-3 2a11 11 0 0 0 6 6l2-3 5 2v2a2 2 0 0 1-2 2A16 16 0 0 1 3 5z",
  "phone-outgoing": "M23 3l-8 8M15 3h8v8M3 5a2 2 0 0 1 2-2h2l2 5-3 2a11 11 0 0 0 6 6l2-3 5 2v2a2 2 0 0 1-2 2A16 16 0 0 1 3 5z",
  target: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  bolt: "M13 2L3 14h7l-1 8 10-12h-7l1-8z",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
};

export function Icon({
  name,
  className = "h-5 w-5",
  strokeWidth = 1.8,
}: {
  name: IconName;
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
