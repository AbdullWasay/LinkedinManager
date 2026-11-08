// Prefer same-origin `/api` (Next rewrite → backend) so the login cookie stays first-party.
const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
      const next = window.location.pathname;
      if (next !== "/login") {
        window.location.href = "/login";
      }
    }
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Profile = {
  id: string;
  user_id: string;
  full_name: string;
  linkedin_url: string;
  portfolio_url: string;
  education: Record<string, unknown>;
  professional_background: {
    current_role?: string;
    summary?: string;
    skills?: string[];
    focus_areas?: string[];
  };
  projects: Array<{ name: string; description?: string }>;
  target_positions: string[];
  target_markets: string[];
  salary_expectations: Record<string, unknown>;
  employment_types: string[];
  match_weights: Record<string, number>;
};

export type Settings = {
  id: string;
  user_id: string;
  automation_paused: boolean;
  emergency_stop: boolean;
  auto_send_enabled: boolean;
  discovery_interval_hours: number;
  sheets_sync_interval_minutes: number;
  daily_send_limit: number;
  follow_up_days: number[];
  extra: Record<string, unknown>;
  version: number;
};

export type AuthStatus = {
  authenticated: boolean;
  auth_required?: boolean;
  login_methods?: { password?: boolean; google?: boolean };
  user_id?: string;
  email?: string;
  name?: string;
  google_connected: boolean;
  scopes: string[];
  spreadsheet_id?: string | null;
  spreadsheet_url?: string | null;
  drive_folder_id?: string | null;
  google_configured: boolean;
};

export type SessionUser = {
  authenticated: boolean;
  auth_required: boolean;
  email?: string | null;
  name?: string | null;
  user_id?: string | null;
  login_methods?: { password?: boolean; google?: boolean };
};

export type AnalyticsOverview = {
  jobs_discovered: number;
  avg_match_score: number;
  pending_approvals: number;
  emails_sent: number;
  emails_ready_to_send: number;
  applications_sent: number;
  interviews: number;
  email_outreach_jobs?: number;
  manual_apply_pending?: number;
  applications_by_stage: Record<string, number>;
  next_send?: NextSendInfo;
};

export type NextSendInfo = {
  status?: string;
  seconds_until_start?: number | null;
  timezone?: string | null;
  local_window?: string;
  message?: string;
  any_open_now?: boolean;
  starts_at?: string | null;
  emails_ready?: number;
  emails_in_next_batch?: number;
  daily_send_limit?: number;
  sent_today?: number;
  remaining_today?: number;
};

export type ActivitySummaryItem = {
  key: string;
  title: string;
  count: number;
  created_at: string | null;
  details: Record<string, unknown>;
};

export type DailyPoint = {
  date: string;
  label?: string;
  jobs_found: number;
  emails_sent: number;
};

export type ApplicationItem = {
  id: string;
  stage: string;
  notes?: string | null;
  thread_id?: string | null;
  updated_at?: string | null;
  job_title?: string | null;
  job_location?: string | null;
  source_url?: string | null;
  match_score?: number | null;
  opportunity_type?: string | null;
  job_source?: string | null;
  company_name?: string | null;
  contact_email?: string | null;
  contact_name?: string | null;
};

export type ActivityLog = {
  id: string;
  category: string;
  action: string;
  status: string;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type SyncStatus = {
  spreadsheet_id?: string | null;
  spreadsheet_url?: string | null;
  resources: Array<{
    resource: string;
    last_pulled_at?: string | null;
    last_pushed_at?: string | null;
    last_error?: string | null;
  }>;
};

export const api = {
  health: () => request<{ status: string; db: boolean; redis: boolean }>("/health"),
  getProfile: () => request<Profile>("/profile"),
  updateProfile: (body: Partial<Profile>) =>
    request<Profile>("/profile", { method: "PUT", body: JSON.stringify(body) }),
  getSettings: () => request<Settings>("/settings"),
  updateSettings: (body: Partial<Settings>) =>
    request<Settings>("/settings", { method: "PATCH", body: JSON.stringify(body) }),
  pauseAutomation: () => request<Settings>("/automation/pause", { method: "POST" }),
  resumeAutomation: () => request<Settings>("/automation/resume", { method: "POST" }),
  emergencyStop: () => request<Settings>("/automation/emergency-stop", { method: "POST" }),
  authStatus: () => request<AuthStatus>("/auth/status"),
  me: () => request<SessionUser>("/auth/me"),
  login: (password: string) =>
    request<{ ok: boolean; email?: string; message?: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  consumeHandoff: (token: string) =>
    request<{ ok: boolean; email?: string; message?: string }>("/auth/session", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  disconnectGoogle: () => request<{ ok: boolean }>("/auth/google/disconnect", { method: "POST" }),
  // Empty NEXT_PUBLIC_API_URL = same-origin /api rewrite on Vercel (never fall back to localhost).
  googleLoginUrl: `${(process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "")}/api/v1/auth/google/login`,
  syncStatus: () => request<SyncStatus>("/sync/status"),
  pushSheets: () => request<Record<string, unknown>>("/sync/sheets/push", { method: "POST" }),
  pullSheets: () => request<Record<string, unknown>>("/sync/sheets/pull", { method: "POST" }),
  fullSync: () => request<Record<string, unknown>>("/sync/sheets/full", { method: "POST" }),
  analytics: () => request<AnalyticsOverview>("/analytics/overview"),
  analyticsDaily: (rangeOrDays: string | number = "7d") => {
    const query =
      typeof rangeOrDays === "number"
        ? `days=${rangeOrDays}`
        : `range=${encodeURIComponent(rangeOrDays)}`;
    return request<{
      range?: string;
      days: number | null;
      series: DailyPoint[];
      totals: { jobs_found: number; emails_sent: number };
    }>(`/analytics/daily?${query}`);
  },
  activitySummary: (limit = 20) =>
    request<{ items: ActivitySummaryItem[] }>(`/analytics/activity-summary?limit=${limit}`),
  nextSend: () => request<NextSendInfo>("/analytics/next-send"),
  applications: (stage?: string, limit = 50) =>
    request<{ total: number; items: ApplicationItem[] }>(
      `/applications?limit=${limit}${stage ? `&stage=${encodeURIComponent(stage)}` : ""}`
    ),
  activityLogs: (limit = 30) => request<ActivityLog[]>(`/activity-logs?limit=${limit}`),
  reconcileEmails: () =>
    request<{ count: number; messages: unknown[] }>("/emails/reconcile", { method: "POST" }),
};
