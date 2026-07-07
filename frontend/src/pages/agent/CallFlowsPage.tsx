import { PageHeader, Card, Badge } from "@/components/ui/Primitives";
import { Icon, type IconName } from "@/components/ui/Icon";
import { SubNav } from "@/components/ui/Bits";
import { AGENT_SUBNAV } from "./KnowledgeBasePage";

const FLOW: { icon: IconName; title: string; desc: string; accent: string }[] = [
  { icon: "wave", title: "Greeting", desc: "Warm intro in Hindi/English", accent: "from-brand-500 to-violet-500" },
  { icon: "target", title: "Qualification", desc: "Budget, area, timeline", accent: "from-cyan-500 to-sky-500" },
  { icon: "home", title: "Property Discussion", desc: "Pitch matching projects", accent: "from-emerald-500 to-teal-500" },
  { icon: "calendar", title: "Appointment Booking", desc: "Lock a site visit", accent: "from-amber-500 to-orange-500" },
  { icon: "users", title: "Human Transfer", desc: "Warm hand-off for hot leads", accent: "from-rose-500 to-pink-500" },
  { icon: "check", title: "Call End", desc: "Summarise & follow up", accent: "from-slate-600 to-slate-500" },
];

export function CallFlowsPage() {
  return (
    <div>
      <PageHeader title="Call Flows" subtitle="How Priya moves a conversation from hello to booked" />
      <SubNav items={AGENT_SUBNAV} />

      <Card className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="font-bold text-slate-900">Default flow</h2>
          <Badge tone="amber">Visual editor coming soon</Badge>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {FLOW.map((s, i) => (
            <div key={s.title} className="relative">
              <div className="card p-5">
                <div className="flex items-center gap-3">
                  <span className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${s.accent} text-white`}>
                    <Icon name={s.icon} className="h-5 w-5" />
                  </span>
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500">{i + 1}</span>
                </div>
                <h3 className="mt-3 font-bold text-slate-900">{s.title}</h3>
                <p className="text-sm text-slate-500">{s.desc}</p>
              </div>
              {i < FLOW.length - 1 && (
                <div className="hidden md:block">
                  <Icon name="chevron-right" className="absolute -right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-300" />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-center gap-2 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
          <Icon name="flow" className="h-5 w-5" />
          A drag-and-drop flow builder to customise these steps, add branches and conditions is on the way.
        </div>
      </Card>
    </div>
  );
}
