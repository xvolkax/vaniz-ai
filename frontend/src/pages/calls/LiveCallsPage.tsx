import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Room } from "livekit-client";
import { api } from "@/lib/api";
import type { ActiveCall, ListenToken } from "@/lib/types";
import { Card, PageHeader, Button, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav, EmptyState } from "@/components/ui/Bits";
import { CALLS_SUBNAV } from "./CallHistoryPage";
import { relativeTime, titleCase } from "@/lib/format";
import { useAuth } from "@/auth/AuthContext";

export function LiveCallsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [listening, setListening] = useState<string | null>(null);
  const roomRef = useRef<Room | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["calls-active"],
    queryFn: () => api.get<{ items: ActiveCall[] }>("/calls/active"),
    refetchInterval: 4000,
  });

  const hangup = useMutation({
    mutationFn: (id: string) => api.post(`/calls/${id}/hangup`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calls-active"] }),
    onError: (e) => alert(e instanceof Error ? e.message : "Failed to end call"),
  });

  async function stopListening() {
    if (roomRef.current) {
      await roomRef.current.disconnect();
      roomRef.current = null;
    }
    setListening(null);
  }

  const listen = useMutation({
    mutationFn: (id: string) => api.post<ListenToken>(`/calls/${id}/listen-token`),
    onSuccess: async (tok, id) => {
      try {
        await stopListening();
        const { Room, RoomEvent } = await import("livekit-client");
        const room = new Room();
        room.on(RoomEvent.TrackSubscribed, (track) => {
          if (track.kind === "audio" && audioRef.current) {
            track.attach(audioRef.current);
          }
        });
        await room.connect(tok.url, tok.token);
        roomRef.current = room;
        setListening(id);
      } catch (e) {
        alert(e instanceof Error ? e.message : "Could not connect audio");
      }
    },
    onError: (e) => alert(e instanceof Error ? e.message : "Listen unavailable"),
  });

  // Cleanup on unmount
  useEffect(() => () => { void roomRef.current?.disconnect(); }, []);

  const items = data?.items ?? [];

  return (
    <div>
      <PageHeader
        title="Live Calls"
        subtitle="Calls Priya is handling right now"
        actions={<Badge tone="green" dot>Live · auto-refresh</Badge>}
      />
      <SubNav items={CALLS_SUBNAV} />

      {/* Hidden audio sink for live listen */}
      <audio ref={audioRef} autoPlay className="hidden" />

      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-400">Checking for active calls…</Card>
      ) : items.length === 0 ? (
        <EmptyState
          icon="phone-live"
          title="No live calls right now"
          hint="When a campaign is running, active conversations appear here. You can listen in live or end a call."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((c) => {
            const isListening = listening === c.id;
            return (
              <Card key={c.id} className="p-5">
                <div className="flex items-center gap-3">
                  <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white">
                    <Icon name="phone-live" className="h-5 w-5" />
                    <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-xl bg-emerald-400/60" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-bold text-slate-900">{c.lead_name || c.phone_number}</p>
                    <p className="text-xs text-slate-400">{c.phone_number} · {titleCase(c.direction)} · started {relativeTime(c.started_at)}</p>
                  </div>
                  {isListening && <Badge tone="cyan" dot>Listening</Badge>}
                </div>
                {hasRole("agent") && (
                  <div className="mt-4 flex gap-2">
                    {isListening ? (
                      <Button variant="secondary" className="flex-1" onClick={() => void stopListening()}>
                        <Icon name="x" className="h-4 w-4" /> Stop listening
                      </Button>
                    ) : (
                      <Button variant="secondary" className="flex-1" disabled={listen.isPending} onClick={() => listen.mutate(c.id)}>
                        <Icon name="play" className="h-4 w-4" /> Listen live
                      </Button>
                    )}
                    <Button variant="danger" className="flex-1" disabled={hangup.isPending} onClick={() => confirm("End this call?") && hangup.mutate(c.id)}>
                      <Icon name="x" className="h-4 w-4" /> End call
                    </Button>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
