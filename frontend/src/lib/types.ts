// Types mirroring the FastAPI response/request schemas (priya.api.schemas).

export type UserRole = "owner" | "admin" | "agent" | "viewer";
export type LeadStatus =
  | "new"
  | "qualifying"
  | "qualified"
  | "unqualified"
  | "booked"
  | "lost";
export type LeadSource =
  | "inbound_call"
  | "outbound_call"
  | "manual"
  | "csv_import"
  | "api"
  | "other";
export type PropertyType =
  | "apartment"
  | "villa"
  | "plot"
  | "commercial"
  | "other";
export type CallDirection = "inbound" | "outbound";
export type CallOutcome =
  | "completed"
  | "not_interested"
  | "callback_requested"
  | "transfer_requested"
  | "no_answer"
  | "failed"
  | "voicemail";
export type AppointmentType = "site_visit" | "callback" | "agent_transfer";
export type AppointmentStatus =
  | "scheduled"
  | "confirmed"
  | "cancelled"
  | "completed";
export type CampaignStatus =
  | "draft"
  | "running"
  | "paused"
  | "completed"
  | "failed";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  phone_number: string | null;
  builder_name: string | null;
  region: string | null;
  created_at: string;
}

export interface Property {
  id: string;
  tenant_id: string;
  slug: string | null;
  project_name: string;
  property_type: PropertyType;
  location: string | null;
  price: string | null;
  total_cost: string | null;
  possession: string | null;
  carpet_area: string | null;
  parking: string | null;
  maintenance: string | null;
  construction_status: string | null;
  rera: string | null;
  connectivity: string | null;
  road_width: string | null;
  amenities: string[];
  price_min: number | null;
  price_max: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  tenant_id: string | null;
  name: string | null;
  phone_number: string;
  city: string | null;
  property_type: PropertyType | null;
  budget_min: number | null;
  budget_max: number | null;
  preferred_location: string | null;
  buying_timeline: string | null;
  purpose: string | null;
  loan_required: boolean | null;
  site_visit_interest: boolean | null;
  preferred_language: string;
  status: LeadStatus;
  source: LeadSource;
  qualification_score: number | null;
  crm_external_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CallSummaryItem {
  id: string;
  direction: CallDirection;
  outcome: CallOutcome | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
}

export interface AppointmentItem {
  id: string;
  type: AppointmentType;
  status: AppointmentStatus;
  scheduled_at: string;
  duration_minutes: number;
  location: string | null;
  notes: string | null;
}

export interface LeadDetail extends Lead {
  calls: CallSummaryItem[];
  appointments: AppointmentItem[];
}

export interface LeadImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: { row: number; error: string }[];
}

export interface CallListItem {
  id: string;
  lead_id: string | null;
  lead_name: string | null;
  phone_number: string | null;
  direction: CallDirection;
  call_date: string;
  duration_seconds: number | null;
  outcome: CallOutcome | null;
  qualification_score: number | null;
  recording_url: string | null;
}

export interface ActiveCall {
  id: string;
  lead_id: string | null;
  lead_name: string | null;
  phone_number: string | null;
  direction: CallDirection;
  started_at: string;
}

export interface ListenToken {
  url: string;
  token: string;
  room: string;
}

export interface LatencyMetrics {
  avg_stt_latency_ms: number | null;
  avg_llm_latency_ms: number | null;
  avg_tts_latency_ms: number | null;
  avg_e2e_latency_ms: number | null;
  user_interruptions: number;
}

export interface CallDetail {
  id: string;
  tenant_id: string | null;
  lead_id: string | null;
  lead_name: string | null;
  phone_number: string | null;
  campaign_id: string | null;
  direction: CallDirection;
  room_name: string | null;
  from_number: string | null;
  to_number: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  outcome: CallOutcome | null;
  final_state: string | null;
  recording_url: string | null;
  transcript: { role?: string; text?: string }[] | null;
  summary: string | null;
  key_requirements: string | null;
  qualification_score: number | null;
  recommended_next_action: string | null;
  follow_up_recommendation: string | null;
  appointments: AppointmentItem[];
  latency: LatencyMetrics;
}

export interface RecentAppointment {
  id: string;
  lead_id: string | null;
  lead_name: string | null;
  type: AppointmentType;
  status: AppointmentStatus;
  scheduled_at: string;
  location: string | null;
}

export interface DashboardSummary {
  calls_today: number;
  calls_this_month: number;
  answered_calls: number;
  interested_leads: number;
  site_visits_booked: number;
  callback_requests: number;
  hot_leads: number;
  conversion_rate: number;
  recent_calls: CallListItem[];
  recent_appointments: RecentAppointment[];
  recent_hot_leads: Lead[];
}

export interface AnalyticsOverview {
  period_days: number;
  total_calls: number;
  answered_calls: number;
  answer_rate: number;
  avg_call_duration_seconds: number | null;
  avg_e2e_latency_ms: number | null;
  total_leads: number;
  qualified_leads: number;
  hot_leads: number;
  avg_qualification_score: number | null;
  site_visits: number;
  callbacks: number;
  conversion_rate: number;
}

export interface BreakdownResponse {
  period_days: number;
  total: number;
  items: { key: string; count: number; percentage: number }[];
}

export interface ConversionTrends {
  period_days: number;
  points: {
    date: string;
    calls: number;
    answered: number;
    site_visits: number;
    new_leads: number;
  }[];
}

export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  status: CampaignStatus;
  concurrency: number;
  max_attempts: number;
  retry_delay_minutes: number;
  working_hours_start: number;
  working_hours_end: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface CampaignAnalytics {
  campaign_id: string;
  total_leads: number;
  attempted: number;
  connected: number;
  interested: number;
  callbacks: number;
  site_visits: number;
  conversion_rate: number;
  status_breakdown: Record<string, number>;
}
