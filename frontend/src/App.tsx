import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { Layout } from "@/components/Layout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { CallHistoryPage } from "@/pages/calls/CallHistoryPage";
import { LiveCallsPage } from "@/pages/calls/LiveCallsPage";
import { RecordingsPage } from "@/pages/calls/RecordingsPage";
import { TranscriptsPage } from "@/pages/calls/TranscriptsPage";
import { CampaignsPage } from "@/pages/campaigns/CampaignsPage";
import { CreateCampaignPage } from "@/pages/campaigns/CreateCampaignPage";
import { CampaignDetailPage } from "@/pages/campaigns/CampaignDetailPage";
import { LeadListsPage } from "@/pages/campaigns/LeadListsPage";
import { ScheduledCallsPage } from "@/pages/campaigns/ScheduledCallsPage";
import { AgentSettingsPage } from "@/pages/agent/AgentSettingsPage";
import { PromptBuilderPage } from "@/pages/agent/PromptBuilderPage";
import { KnowledgeBasePage } from "@/pages/agent/KnowledgeBasePage";
import { VoiceSettingsPage } from "@/pages/agent/VoiceSettingsPage";
import { CallFlowsPage } from "@/pages/agent/CallFlowsPage";
import { AppointmentsPage } from "@/pages/AppointmentsPage";
import { LeadsPage } from "@/pages/LeadsPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { SettingsPage } from "@/pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />

          <Route path="/calls" element={<Navigate to="/calls/history" replace />} />
          <Route path="/calls/live" element={<LiveCallsPage />} />
          <Route path="/calls/history" element={<CallHistoryPage />} />
          <Route path="/calls/recordings" element={<RecordingsPage />} />
          <Route path="/calls/transcripts" element={<TranscriptsPage />} />

          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/campaigns/new" element={<CreateCampaignPage />} />
          <Route path="/campaigns/lead-lists" element={<LeadListsPage />} />
          <Route path="/campaigns/scheduled" element={<ScheduledCallsPage />} />
          <Route path="/campaigns/:id" element={<CampaignDetailPage />} />

          <Route path="/agent" element={<Navigate to="/agent/settings" replace />} />
          <Route path="/agent/settings" element={<AgentSettingsPage />} />
          <Route path="/agent/prompt" element={<PromptBuilderPage />} />
          <Route path="/agent/knowledge" element={<KnowledgeBasePage />} />
          <Route path="/agent/voice" element={<VoiceSettingsPage />} />
          <Route path="/agent/flows" element={<CallFlowsPage />} />

          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
