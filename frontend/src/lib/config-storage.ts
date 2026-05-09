/** Shown as the session title on `/main`; blank saves as empty and falls back here. */
export const DEFAULT_SESSION_TITLE = "Untitled curriculum";

export type CurriculumConfig = {
  /** Friendly label for this run; optional for older saved configs */
  sessionName?: string;
  curriculum: string;
  content: string;
  /** Full vision/mission text (from template and/or free text) */
  visionMission?: string;
  /** Who the learners are, including age / cohort context */
  targetStudentsDescription?: string;
  bloomLevels: string[];
  durationWeeks: number;
  classRatePerWeek: number;
  totalStudents: number;
};

const STORAGE_KEY = "kari-curriculum-config";

export function saveConfig(config: CurriculumConfig): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function clearConfig(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}

export function loadConfig(): CurriculumConfig | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurriculumConfig;
  } catch {
    return null;
  }
}
