import { useState } from "react";
import { Card, PageHeader, Button, Textarea, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav } from "@/components/ui/Bits";
import { AGENT_SUBNAV } from "./KnowledgeBasePage";

const TEMPLATES = [
  "Qualify the lead's budget, preferred location and timeline, then book a site visit.",
  "Re-engage old leads warmly and check if they're still looking to buy.",
  "Answer project questions confidently and push for a weekend site visit.",
];

export function PromptBuilderPage() {
  const [basic, setBasic] = useState(
    "You are Priya, a friendly real-estate sales assistant. Greet the caller, understand what they're looking for, share matching projects, and book a site visit."
  );
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [system, setSystem] = useState("");

  return (
    <div>
      <PageHeader title="Prompt Builder" subtitle="Tell Priya how to handle your calls — in plain language" />
      <SubNav items={AGENT_SUBNAV} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card className="p-6">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-bold text-slate-900">What should the AI do?</h2>
              <Badge tone="green" dot>Basic mode</Badge>
            </div>
            <p className="mb-3 text-sm text-slate-500">Describe Priya's goal in a sentence or two. That's all most brokers ever need.</p>
            <Textarea value={basic} onChange={(e) => setBasic(e.target.value)} className="min-h-[160px]" />
            <div className="mt-3 flex flex-wrap gap-2">
              {TEMPLATES.map((t) => (
                <button key={t} onClick={() => setBasic(t)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700">
                  {t.length > 46 ? t.slice(0, 46) + "…" : t}
                </button>
              ))}
            </div>
          </Card>

          <Card className="overflow-hidden">
            <button onClick={() => setAdvancedOpen((o) => !o)} className="flex w-full items-center justify-between px-6 py-4 text-left">
              <div>
                <h2 className="font-bold text-slate-900">Advanced</h2>
                <p className="text-xs text-slate-400">System prompt — only if you really need it</p>
              </div>
              <Icon name={advancedOpen ? "chevron-down" : "chevron-right"} className="h-5 w-5 text-slate-400" />
            </button>
            {advancedOpen && (
              <div className="border-t border-slate-100 px-6 py-5">
                <Textarea placeholder="Full system prompt (optional)…" value={system} onChange={(e) => setSystem(e.target.value)} className="min-h-[180px] font-mono text-xs" />
                <p className="mt-2 text-xs text-slate-400">Most users never need this. The Basic instruction plus your Knowledge Base is usually enough.</p>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <h3 className="font-bold text-slate-900">Preview</h3>
            <div className="mt-3 space-y-2">
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-brand-50 px-3 py-2 text-sm text-slate-800">Namaste! Main Priya bol rahi hoon. Aap kis area mein property dhoond rahe hain?</div>
              <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-slate-100 px-3 py-2 text-sm text-slate-700">Noida mein 2BHK chahiye, budget 50 lakh.</div>
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-brand-50 px-3 py-2 text-sm text-slate-800">Bahut badhiya! Iske liye ek site visit book kar dun?</div>
            </div>
          </Card>
          <div className="flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <Icon name="sparkles" className="h-4 w-4" /> Saving custom prompts per workspace is coming soon.
          </div>
          <Button className="w-full" disabled>Save prompt</Button>
        </div>
      </div>
    </div>
  );
}
