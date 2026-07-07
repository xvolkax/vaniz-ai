import { Badge, type Tone } from "@/components/ui/Primitives";
import { titleCase } from "@/lib/format";
import type {
  AppointmentStatus,
  CallOutcome,
  CampaignStatus,
  LeadStatus,
} from "@/lib/types";

const LEAD: Record<LeadStatus, Tone> = {
  new: "blue",
  qualifying: "amber",
  qualified: "green",
  booked: "purple",
  unqualified: "slate",
  lost: "red",
};
export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return <Badge tone={LEAD[status]} dot>{titleCase(status)}</Badge>;
}

const OUTCOME: Record<CallOutcome, Tone> = {
  completed: "green",
  callback_requested: "amber",
  transfer_requested: "purple",
  not_interested: "slate",
  no_answer: "red",
  failed: "red",
  voicemail: "amber",
};
export function OutcomeBadge({ outcome }: { outcome: CallOutcome | null }) {
  if (!outcome) return <Badge tone="slate">In progress</Badge>;
  return <Badge tone={OUTCOME[outcome]}>{titleCase(outcome)}</Badge>;
}

const CAMPAIGN: Record<CampaignStatus, Tone> = {
  draft: "slate",
  running: "green",
  paused: "amber",
  completed: "blue",
  failed: "red",
};
export function CampaignStatusBadge({ status }: { status: CampaignStatus }) {
  return <Badge tone={CAMPAIGN[status]} dot>{titleCase(status)}</Badge>;
}

const APPT: Record<AppointmentStatus, Tone> = {
  scheduled: "blue",
  confirmed: "green",
  completed: "purple",
  cancelled: "red",
};
export function AppointmentStatusBadge({ status }: { status: AppointmentStatus }) {
  return <Badge tone={APPT[status]}>{titleCase(status)}</Badge>;
}

/** Lead temperature derived from qualification score (0-100). */
export function temperature(score: number | null): { label: string; tone: Tone } {
  if (score == null) return { label: "Unscored", tone: "slate" };
  if (score >= 70) return { label: "Hot", tone: "red" };
  if (score >= 45) return { label: "Warm", tone: "amber" };
  return { label: "Cold", tone: "cyan" };
}
export function TemperatureBadge({ score }: { score: number | null }) {
  const t = temperature(score);
  return <Badge tone={t.tone} dot>{t.label}</Badge>;
}

export function ScorePill({ score }: { score: number | null }) {
  if (score == null) return <span className="text-slate-300">—</span>;
  const tone = score >= 70 ? "green" : score >= 45 ? "amber" : "slate";
  return <Badge tone={tone as Tone}>{score}</Badge>;
}
