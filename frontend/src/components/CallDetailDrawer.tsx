import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallDetail } from "@/lib/types";
import { Drawer } from "@/components/ui/Drawer";
import { Badge, type Tone } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Bits";
import { OutcomeBadge, ScorePill } from "@/components/StatusBadges";
import { formatDateTime, formatDuration, titleCase } from "@/lib/format";

function sentiment(outcome: string | null, score: number | null): { label: string; tone: Tone } {
  if (outcome === "not_interested") return { label: "Negative", tone: "red" };
  if (outcome === "completed" && (score ?? 0) >= 60) return { label: "Positive", tone: "green" };
  if (outcome === "callback_requested") return { label: "Neutral", tone: "amber" };
  if ((score ?? 0) >= 45) return { label: "Positive", tone: "green" };
  return { label: "Neutral", tone: "slate" };
}

function deriveTags(c: CallDetail): { label: string; tone: Tone }[] {
  const tags: { label: string; tone: Tone }[] = [];
  if ((c.qualification_score ?? 0) >= 70) tags.push({ label: "Hot Lead", tone: "red" });
  else if ((c.qualification_score ?? 0) >= 45) tags.push({ label: "Warm Lead", tone: "amber" });
  if (c.outcome) tags.push({ label: titleCase(c.outcome), tone: "blue" });
  if (c.appointments.some((a) => a.type === "site_visit")) tags.push({ label: "Site Visit", tone: "purple" });
  if (c.appointments.some((a) => a.type === "callback")) tags.push({ label: "Callback", tone: "cyan" });
  return tags;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-4">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</h4>
      {children}
    </div>
  );
}

export function CallDetailDrawer({ callId, onClose }: { callId: string | null; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["call", callId],
    queryFn: () => api.get<CallDetail>(`/calls/${callId}`),
    enabled: !!callId,
  });

  return (
    <Drawer
      open={!!callId}
      onClose={onClose}
      title={data ? data.lead_name || data.phone_number || "Call" : "Call detail"}
      subtitle={data ? `${titleCase(data.direction)} · ${formatDateTime(data.started_at)}` : undefined}
    >
      {isLoading || !data ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* header stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="card p-3 text-center">
              <p className="text-xs text-slate-400">Duration</p>
              <p className="mt-0.5 font-bold text-slate-800">{formatDuration(data.duration_seconds)}</p>
            </div>
            <div className="card p-3 text-center">
              <p className="text-xs text-slate-400">Lead Score</p>
              <p className="mt-0.5"><ScorePill score={data.qualification_score} /></p>
            </div>
            <div className="card p-3 text-center">
              <p className="text-xs text-slate-400">Sentiment</p>
              <p className="mt-0.5">
                {(() => {
                  const s = sentiment(data.outcome, data.qualification_score);
                  return <Badge tone={s.tone}>{s.label}</Badge>;
                })()}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <OutcomeBadge outcome={data.outcome} />
            {deriveTags(data).map((t) => (
              <Badge key={t.label} tone={t.tone}>{t.label}</Badge>
            ))}
          </div>

          {data.summary && (
            <Section title="AI Summary">
              <p className="text-sm leading-relaxed text-slate-700">{data.summary}</p>
            </Section>
          )}
          {data.key_requirements && (
            <Section title="Key Requirements">
              <p className="text-sm text-slate-700">{data.key_requirements}</p>
            </Section>
          )}
          {(data.recommended_next_action || data.follow_up_recommendation) && (
            <Section title="Recommended Next Steps">
              {data.recommended_next_action && (
                <p className="text-sm text-slate-700">→ {data.recommended_next_action}</p>
              )}
              {data.follow_up_recommendation && (
                <p className="mt-1 text-sm text-slate-500">{data.follow_up_recommendation}</p>
              )}
            </Section>
          )}

          {/* Recording (not stored yet) */}
          <div className="flex items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white/60 p-4">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
              <Icon name="recording" className="h-5 w-5" />
            </span>
            <div className="text-sm">
              <p className="font-medium text-slate-700">Call recording</p>
              <p className="text-xs text-slate-400">Recording capture is coming soon.</p>
            </div>
          </div>

          {/* Transcript */}
          <Section title="Transcript">
            {!data.transcript || data.transcript.length === 0 ? (
              <p className="text-sm text-slate-400">No transcript available.</p>
            ) : (
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {data.transcript.map((t, i) => {
                  const isAgent = t.role === "assistant";
                  return (
                    <div key={i} className={`flex ${isAgent ? "justify-start" : "justify-end"}`}>
                      <div
                        className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                          isAgent
                            ? "rounded-tl-sm bg-brand-50 text-slate-800"
                            : "rounded-tr-sm bg-slate-100 text-slate-700"
                        }`}
                      >
                        <span className="mb-0.5 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                          {isAgent ? "Priya" : "Caller"}
                        </span>
                        {t.text}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Section>

          {/* Timeline */}
          <Section title="Timeline">
            <ol className="relative ml-2 space-y-3 border-l border-slate-200 pl-4">
              <li className="text-sm">
                <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-brand-500" />
                <span className="font-medium text-slate-700">Call started</span>
                <span className="ml-2 text-xs text-slate-400">{formatDateTime(data.started_at)}</span>
              </li>
              {data.appointments.map((a) => (
                <li key={a.id} className="text-sm">
                  <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="font-medium text-slate-700">{titleCase(a.type)} booked</span>
                  <span className="ml-2 text-xs text-slate-400">{formatDateTime(a.scheduled_at)}</span>
                </li>
              ))}
              {data.ended_at && (
                <li className="text-sm">
                  <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-slate-400" />
                  <span className="font-medium text-slate-700">Call ended</span>
                  <span className="ml-2 text-xs text-slate-400">{formatDateTime(data.ended_at)}</span>
                </li>
              )}
            </ol>
          </Section>

          {/* Latency */}
          <Section title="Quality Metrics">
            <div className="grid grid-cols-4 gap-2 text-center">
              {[
                ["STT", data.latency.avg_stt_latency_ms],
                ["LLM", data.latency.avg_llm_latency_ms],
                ["TTS", data.latency.avg_tts_latency_ms],
                ["E2E", data.latency.avg_e2e_latency_ms],
              ].map(([k, v]) => (
                <div key={k as string} className="rounded-lg bg-slate-50 p-2">
                  <p className="text-[10px] uppercase text-slate-400">{k}</p>
                  <p className="text-sm font-semibold text-slate-700">
                    {v != null ? `${Math.round(v as number)}ms` : "—"}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}
    </Drawer>
  );
}
