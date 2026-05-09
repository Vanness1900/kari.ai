"use client";

import type { ClassroomState, CurriculumModule, QnaQuestion, TimestepLog } from "@/lib/api";

const PHASE_LABELS: Record<number, string> = {
  1: "Deliver",
  2: "Q&A",
  3: "Exercise",
  4: "Assessment",
  5: "Recap",
};

type TimelineRow = {
  key: string;
  module_index: number;
  timestep: number;
  phaseLabel: string;
  moduleTitle: string;
  questions?: QnaQuestion[];
  lesson?: string;
};

function asQuestions(value: unknown): QnaQuestion[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const out: QnaQuestion[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const q = item as Partial<QnaQuestion>;
    if (typeof q.student_id !== "string") continue;
    if (typeof q.name !== "string") continue;
    if (typeof q.question !== "string") continue;
    out.push({ student_id: q.student_id, name: q.name, question: q.question });
  }
  return out.length ? out : undefined;
}

function asText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const t = value.trim();
  return t ? t : undefined;
}

export function TeachingQnaTimeline({
  state,
  modules,
  events,
  className,
}: {
  state: ClassroomState | null;
  modules?: CurriculumModule[];
  events: TimestepLog[];
  className?: string;
}) {
  const moduleList = modules ?? state?.curriculum.modules ?? [];

  const byKey = new Map<string, TimelineRow>();
  const ensureRow = (m: number, t: number): TimelineRow => {
    const key = `${m}:${t}`;
    const existing = byKey.get(key);
    if (existing) return existing;
    const mod = moduleList[m];
    const phaseLabel = PHASE_LABELS[t] ?? `Step ${t}`;
    const row: TimelineRow = {
      key,
      module_index: m,
      timestep: t,
      phaseLabel,
      moduleTitle: mod?.title ?? `Module ${m + 1}`,
    };
    byKey.set(key, row);
    return row;
  };

  for (const e of events) {
    const m = Number(e.module_index);
    const t = Number(e.timestep);
    if (!Number.isFinite(m) || !Number.isFinite(t)) continue;
    if (e.agent === "student_questions") {
      const row = ensureRow(m, t);
      const payload = e.payload ?? {};
      row.questions = asQuestions((payload as Record<string, unknown>).questions);
      continue;
    }
    if (e.agent === "teacher") {
      const row = ensureRow(m, t);
      const payload = e.payload ?? {};
      row.lesson = asText((payload as Record<string, unknown>).lesson);
      continue;
    }
  }

  // Fallback: while live polling, newest teacher lesson might not be in events yet.
    if (state) {
    const key = `${state.current_module}:${state.current_timestep}`;
    const row = ensureRow(state.current_module, state.current_timestep);
    if (!row.lesson) row.lesson = asText(state.current_lesson);
    if (state.current_timestep === 2 && (!row.questions || row.questions.length === 0)) {
      row.questions = state.qna_student_questions ?? [];
    }
    byKey.set(key, row);
  }

  const rows = Array.from(byKey.values())
    .filter((r) => r.lesson || (r.questions && r.questions.length > 0))
    .sort((a, b) =>
      a.module_index !== b.module_index
        ? a.module_index - b.module_index
        : a.timestep - b.timestep,
    );

  if (rows.length === 0) {
    return (
      <div
        className={
          className ??
          "rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-sm text-slate-500"
        }
      >
        Timeline will appear once the simulation starts producing teacher steps.
      </div>
    );
  }

  return (
    <div className={className ?? "rounded-2xl border border-slate-200 bg-white shadow-sm"}>
      <div className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white px-5 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
          Teaching log
        </p>
        <h3 className="text-sm font-semibold text-slate-900">
          Teacher steps + student Q&amp;A
        </h3>
      </div>
      <ol className="divide-y divide-slate-100">
        {rows.map((row) => {
          const isQna = row.timestep === 2 && (row.questions?.length ?? 0) > 0;
          return (
            <li key={row.key} className="px-5 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-xs font-semibold text-slate-700">
                  Module {row.module_index + 1}: {row.moduleTitle}
                </p>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                  {row.phaseLabel} · Step {row.timestep}/5
                </span>
              </div>

              {isQna && row.questions && (
                <div className="mt-3 space-y-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-600">
                    Questions
                  </p>
                  <ul className="space-y-2">
                    {row.questions.map((q, i) => (
                      <li key={`${q.student_id}-${i}`} className="text-sm text-slate-800">
                        <span className="font-semibold text-slate-700">{q.name}:</span>{" "}
                        {q.question}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {row.lesson && (
                <div className="mt-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-[#1DA1F2]">
                    {isQna ? "Teacher answer" : "Teacher"}
                  </p>
                  <pre className="mt-2 max-h-[360px] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-slate-50 p-3 font-sans text-sm leading-relaxed text-slate-800">
                    {row.lesson}
                  </pre>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

