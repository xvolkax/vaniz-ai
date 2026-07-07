import { PageHeader } from "@/components/ui/Primitives";
import { SubNav, ComingSoon } from "@/components/ui/Bits";
import { CALLS_SUBNAV } from "./CallHistoryPage";

export function RecordingsPage() {
  return (
    <div>
      <PageHeader title="Recordings" subtitle="Listen back to every AI conversation" />
      <SubNav items={CALLS_SUBNAV} />
      <ComingSoon
        icon="recording"
        title="Call recordings"
        description="Full call audio with an in-browser player, waveform scrubbing, search and one-click download — so you can review exactly how Priya spoke to each lead."
        bullets={[
          "Secure per-tenant recording storage",
          "In-line audio player with transcript sync",
          "Search & filter by lead, outcome or date",
          "Download for training & compliance",
        ]}
      />
    </div>
  );
}
