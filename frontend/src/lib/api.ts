/**
 * Typed fetch client for the kari.ai backend.
 *
 * Base URL is read from `NEXT_PUBLIC_API_URL` (defaults to http://localhost:8000).
 * Keep this file the single source of truth for backend response shapes — the live
 * simulation hook and chart components import these types directly.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ||
  "http://localhost:8000";

export type StartRequestBody = {
  session_name?: string;
  curriculum_text?: string;
  content_text?: string;
  vision_mission?: string;
  target_students_description?: string;
  bloom_levels?: string[];
  total_students?: number;
  n_modules?: number;
};

export type StartResponse = {
  status: "running";
  session_id: string;
  students_count: number;
  n_modules: number;
};

export type StatusResponse = {
  session_id: string;
  current_module: number | null;
  current_timestep: number | null;
  students_count: number;
  log_count: number;
  simulation_complete: boolean;
  has_insight: boolean;
  has_error: boolean;
  avg_confusion_last: number | null;
  last_event_at: string | null;
};

export type TimestepLog = {
  agent: string;
  module_index: number;
  timestep: number;
  payload: Record<string, unknown>;
};

export type EventsResponse = {
  session_id: string;
  since: number;
  next_since: number;
  total: number;
  events: TimestepLog[];
  simulation_complete: boolean;
};

export type StudentProfile = {
  id: string;
  name: string;
  learning_style?: string;
  attention_span_mins?: number;
  social_anxiety?: number;
  motivation?: number;
  peer_influence?: number;
  knowledge_state?: Record<string, number>;
  misconceptions?: string[];
  confusion_level?: number;
  attention_remaining?: number;
  cumulative_fatigue?: number;
};

export type CurriculumModule = {
  id: string;
  title: string;
  content: string;
  blooms_level?: number;
};

export type ClassroomState = {
  session_id: string;
  curriculum: { title?: string; modules?: CurriculumModule[] };
  students: StudentProfile[];
  current_module: number;
  current_timestep: number;
  timestep_logs: TimestepLog[];
  module_results: Array<Record<string, unknown>>;
  student_assessments: Record<string, AssessmentRecord> | null;
  simulation_complete: boolean;
  insight_report: InsightReport | null;
  current_lesson: string | null;
  module_delivery_snapshot: string | null;
  qna_student_questions: QnaQuestion[];
  avg_confusion_last?: number;
  simulation_error?: string;
};

export type QnaQuestion = {
  student_id: string;
  name: string;
  question: string;
};

export type AssessmentRecord = {
  student_id: string;
  overall_score: number;
  risk_flags: string[];
  narrative: string;
};

export type InsightReport = {
  summary: string;
  curriculum_critique: string;
  blooms_alignment_notes: string[];
};

export type ReportResponse = {
  session_id: string;
  insight_report: InsightReport | null;
  student_assessments: Record<string, AssessmentRecord>;
  module_results: Array<Record<string, unknown>>;
  students: StudentProfile[];
  curriculum: { title?: string; modules?: CurriculumModule[] };
  timestep_logs: TimestepLog[];
  simulation_error?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${res.statusText} on ${path}: ${text}`);
  }
  return (await res.json()) as T;
}

export function startSimulation(body: StartRequestBody): Promise<StartResponse> {
  return request<StartResponse>("/api/simulation/start", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getStatus(sessionId: string): Promise<StatusResponse> {
  return request<StatusResponse>(
    `/api/simulation/status?id=${encodeURIComponent(sessionId)}`,
  );
}

export function getEvents(
  sessionId: string,
  since: number,
  limit = 200,
): Promise<EventsResponse> {
  return request<EventsResponse>(
    `/api/simulation/events?id=${encodeURIComponent(sessionId)}&since=${since}&limit=${limit}`,
  );
}

export function getState(sessionId: string): Promise<ClassroomState> {
  return request<ClassroomState>(
    `/api/simulation/state?id=${encodeURIComponent(sessionId)}`,
  );
}

export function getReport(sessionId: string): Promise<ReportResponse> {
  return request<ReportResponse>(`/api/report/${encodeURIComponent(sessionId)}`);
}
