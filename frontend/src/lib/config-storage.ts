export type CurriculumConfig = {
  curriculum: string;
  content: string;
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
