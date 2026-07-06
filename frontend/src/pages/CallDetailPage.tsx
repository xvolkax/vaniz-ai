import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CallDetail } from "@/lib/types";
import { Button, Card, PageHeader } from "@/components/ui/Primitives";
import { LoadingBlock } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/States";
import { AppointmentStatusBadge, OutcomeBadge, ScoreBadge } from "@/components/StatusBadges";
import { formatDateTime, formatDuration, titleCase } from "@/lib/format";

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs uppercase text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-slate-800">{value ?? "—"}</p>
    </div>
  );
}

export function CallDetailPage() {
  const { id = "" } = useParams();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["call", id],
    queryFn: () => api.get<CallDetail>(`/calls/${id}`),
  });

  return (
    <div>
      <PageHeader
        title="Call Detail"
        subtitle={data ? `${titleCase(data.direction)} · ${formatDateTime(data.started_at)}` : undefined}
        actions={
          <>
            {data?.lead_id && (
              <Link to={`/leads/${data.lead_id}`}><Button variant="secondary">View lead</Button></Link>
            )}
            <Link to="/calls"><Button variant="secondary">Back</Button></Link>
          </>
        }
      />

      {isLoading && <LoadingBlock />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {data && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card className="p-5">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <OutcomeBadge outcome={data.outcome} />
                <ScoreBadge score={data.qualification_score} />
                <span className="text-sm text-slate-500">
                  {data.lead_name || data.phone_number || "Unknown"}
                </span>
              </div>
              {data.summary && (
                <div className="mb-4">
                  <h3 className="text-xs uppercase text-slate-400">AI Summary</h3>
                  <p className="mt-1 text-sm text-slate-700">{data.summary}</p>
                </div>
              )}
              {data.key_requirements && (
                <div className="mb-4">
                  <h3 className="text-xs uppercase text-slate-400">Key Requirements</h3>
                  <p className="mt-1 text-sm text-slate-700">{data.key_requirements}</p>
                </div>
              )}
              {data.recommended_next_action && (
                <div className="mb-4">
                  <h3 className="text-xs uppercase text-slate-400">Recommended Next Action</h3>
                  <p className="mt-1 text-sm text-slate-700">{data.recommended_next_action}</p>
                </div>
              )}
              {data.follow_up_recommendation && (
                <div>
                  <h3 className="text-xs uppercase text-slate-400">Follow-up</h3>
                  <p className="mt-1 text-sm text-slate-700">{data.follow_up_recommendation}</p>
                </div>
              )}
            </Card>

            <Card className="p-5">
              <h3 className="mb-3 font-semibold text-slate-800">Transcript</h3>
              {!data.transcript || data.transcript.length === 0 ? (
                <p className="text-sm text-slate-500">No transcript available.</p>
              ) : (
                <div className="max-h-96 space-y-2 overflow-y-auto">
                  {data.transcript.map((t, i) => (
                    <div
                      key={i}
                      className={`rounded-lg px-3 py-2 text-sm ${
                        t.role === "assistant"
                          ? "bg-brand-50 text-slate-800"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      <span className="mr-2 text-xs font-medium uppercase text-slate-400">
                        {t.role === "assistant" ? "Priya" : "Caller"}
                      </span>
                      {t.text}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="p-5">
              <h3 className="mb-3 font-semibold text-slate-800">Details</h3>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Duration" value={formatDuration(data.duration_seconds)} />
                <Metric label="Ended" value={data.ended_at ? formatDateTime(data.ended_at) : "—"} />
                <Metric label="From" value={data.from_number} />
                <Metric label="To" value={data.to_number} />
                {data.campaign_id && (
                  <Metric
                    label="Campaign"
                    value={<Link className="text-brand-600 hover:underline" to={`/campaigns/${data.campaign_id}`}>Open</Link>}
                  />
                )}
              </div>
            </Card>

            <Card className="p-5">
              <h3 className="mb-3 font-semibold text-slate-800">Latency (avg)</h3>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="STT ms" value={data.latency.avg_stt_latency_ms?.toFixed(0)} />
                <Metric label="LLM ms" value={data.latency.avg_llm_latency_ms?.toFixed(0)} />
                <Metric label="TTS ms" value={data.latency.avg_tts_latency_ms?.toFixed(0)} />
                <Metric label="E2E ms" value={data.latency.avg_e2e_latency_ms?.toFixed(0)} />
                <Metric label="Interruptions" value={data.latency.user_interruptions} />
              </div>
            </Card>

            {data.appointments.length > 0 && (
              <Card>
                <h3 className="border-b border-slate-100 px-4 py-3 font-semibold text-slate-800">Appointments</h3>
                <div className="divide-y divide-slate-100">
                  {data.appointments.map((a) => (
                    <div key={a.id} className="px-4 py-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{titleCase(a.type)}</span>
                        <AppointmentStatusBadge status={a.status} />
                      </div>
                      <p className="text-xs text-slate-500">{formatDateTime(a.scheduled_at)}</p>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
