import { useState } from "react";
import { Card, PageHeader, Button, Select, Badge } from "@/components/ui/Primitives";
import { Icon } from "@/components/ui/Icon";
import { SubNav } from "@/components/ui/Bits";
import { AGENT_SUBNAV } from "./KnowledgeBasePage";

function Slider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="text-slate-400">{value}%</span>
      </div>
      <input type="range" min={0} max={100} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-brand-600" />
    </div>
  );
}

export function VoiceSettingsPage() {
  const [voice, setVoice] = useState("priya");
  const [speed, setSpeed] = useState(50);
  const [warmth, setWarmth] = useState(70);
  const [energy, setEnergy] = useState(60);

  return (
    <div>
      <PageHeader title="Voice Settings" subtitle="Fine-tune how Priya sounds to your leads" />
      <SubNav items={AGENT_SUBNAV} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-4 font-bold text-slate-900">Voice</h2>
          <div className="space-y-3">
            {[
              { id: "priya", name: "Priya", desc: "Warm, friendly — the default", accent: "from-brand-500 to-violet-500" },
              { id: "neha", name: "Neha", desc: "Energetic and upbeat", accent: "from-amber-500 to-orange-500" },
              { id: "arjun", name: "Arjun", desc: "Calm, professional male voice", accent: "from-cyan-500 to-sky-500" },
            ].map((v) => (
              <button key={v.id} onClick={() => setVoice(v.id)} className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${voice === v.id ? "border-brand-500 bg-brand-50 ring-4 ring-brand-500/10" : "border-slate-200 hover:border-slate-300"}`}>
                <span className={`flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br ${v.accent} text-white`}><Icon name="wave" className="h-5 w-5" /></span>
                <span className="flex-1">
                  <span className="block font-semibold text-slate-800">{v.name}</span>
                  <span className="block text-xs text-slate-400">{v.desc}</span>
                </span>
                <span className="rounded-full p-2 text-slate-400 hover:bg-white hover:text-brand-600" title="Preview coming soon"><Icon name="play" className="h-4 w-4" /></span>
              </button>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-bold text-slate-900">Delivery</h2>
            <Badge tone="amber">Beta</Badge>
          </div>
          <div className="space-y-5">
            <Slider label="Speaking speed" value={speed} onChange={setSpeed} />
            <Slider label="Warmth" value={warmth} onChange={setWarmth} />
            <Slider label="Energy" value={energy} onChange={setEnergy} />
            <div className="grid grid-cols-2 gap-4">
              <Select label="Language"><option>Hindi + English</option><option>English</option></Select>
              <Select label="Accent"><option>Indian</option><option>Neutral</option></Select>
            </div>
          </div>
          <div className="mt-5 flex items-center gap-3">
            <Button disabled><Icon name="play" className="h-4 w-4" /> Preview voice</Button>
            <span className="text-xs text-slate-400">Live voice preview is coming soon.</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
