import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { Layout } from "@/components/Layout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LeadsPage } from "@/pages/LeadsPage";
import { LeadDetailPage } from "@/pages/LeadDetailPage";
import { PropertiesPage } from "@/pages/PropertiesPage";
import { CallsPage } from "@/pages/CallsPage";
import { CallDetailPage } from "@/pages/CallDetailPage";
import { CampaignsPage } from "@/pages/CampaignsPage";
import { CampaignDetailPage } from "@/pages/CampaignDetailPage";
import { AppointmentsPage } from "@/pages/AppointmentsPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { SettingsPage } from "@/pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/leads/:id" element={<LeadDetailPage />} />
          <Route path="/properties" element={<PropertiesPage />} />
          <Route path="/calls" element={<CallsPage />} />
          <Route path="/calls/:id" element={<CallDetailPage />} />
          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
