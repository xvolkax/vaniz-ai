import { Badge } from "@/components/ui/Primitives";
import { titleCase } from "@/lib/format";
import type {
  CallOutcome,
  CampaignStatus,
  LeadStatus,
  AppointmentStatus,
} from "@/lib/types";

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  const tone = {
    new: "blue",
    qualifying: "amber",
    qualified: "green",
    booked: "purple",
    unqualified: "slate",
    lost: "red",
  }[status] as never;
  return <Badge tone={tone}>{titleCase(status)}</Badge>;
}

export function OutcomeBadge({ outcome }: { outcome: CallOutcome | null }) {
  if (!outcome) return <Badge tone="slate">—</Badge>;
  const tone = {
    completed: "green",
    callback_requested: "amber",
    transfer_requested: "purple",
    not_interested: "slate",
    no_answer: "red",
    failed: "red",
    voicemail: "amber",
  }[outcome] as never;
  return <Badge tone={tone}>{titleCase(outcome)}</Badge>;
}

export function CampaignStatusBadge({ status }: { status: CampaignStatus }) {
  const tone = {
    draft: "slate",
    running: "green",
    paused: "amber",
    completed: "blue",
    failed: "red",
  }[status] as never;
  return <Badge tone={tone}>{titleCase(status)}</Badge>;
}

export function AppointmentStatusBadge({ status }: { status: AppointmentStatus }) {
  const tone = {
    scheduled: "blue",
    confirmed: "green",
    completed: "purple",
    cancelled: "red",
  }[status] as never;
  return <Badge tone={tone}>{titleCase(status)}</Badge>;
}

export function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-slate-400">—</span>;
  const tone = score >= 70 ? "green" : score >= 45 ? "amber" : "slate";
  return <Badge tone={tone as never}>{score}</Badge>;
}
