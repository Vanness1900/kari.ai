"use client";

import { Markdown } from "@/components/markdown";
import type {
  ClassroomState,
  CurriculumModule,
  QnaQuestion,
  TimestepLog,
} from "@/lib/api";

const PHASE_LABELS: Record<number, string> = {
  1: "Deliver",
  2: "Q&A",
  3: "Exercise",
  4: "Assessment",
  5: "Recap",
};

type TeacherTurn = {
  kind: "teacher";
  key: string;
  module_index: number;
  timestep: number;
  phaseLabel: string;
  moduleTitle: string;
  lesson: string;
};

type StudentTurn = {
  kind: "students";
  key: string;
  module_index: number;
  timestep: number;
  moduleTitle: string;
  questions: QnaQuestion[];
};

type Turn = TeacherTurn | StudentTurn;

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

function moduleTitle(modules: CurriculumModule[], idx: number): string {
  return modules[idx]?.title ?? `Module ${idx + 1}`;
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

  const teacherByKey = new Map<string, string>();
  const questionsByKey = new Map<string, QnaQuestion[]>();
  const order: string[] = [];

  const recordOrder = (k: string) => {
    if (!order.includes(k)) order.push(k);
  };

  for (const e of events) {
    const m = Number(e.module_index);
    const t = Number(e.timestep);
    if (!Number.isFinite(m) || !Number.isFinite(t)) continue;
    const payload = (e.payload ?? {}) as Record<string, unknown>;

    if (e.agent === "student_questions") {
      const qs = asQuestions(payload.questions);
      if (qs && qs.length > 0) {
        const key = `q:${m}:${t}`;
        questionsByKey.set(key, qs);
        recordOrder(key);
      }
      continue;
    }
    if (e.agent === "teacher") {
      const lesson = asText(payload.lesson);
      if (lesson) {
        const key = `l:${m}:${t}`;
        teacherByKey.set(key, lesson);
        recordOrder(key);
      }
      continue;
    }
  }

  if (state) {
    const m = state.current_module;
    const t = state.current_timestep;
    if (t === 2) {
      const qs = state.qna_student_questions ?? [];
      if (qs.length > 0) {
        const key = `q:${m}:${t}`;
        if (!questionsByKey.has(key)) {
          questionsByKey.set(key, qs);
          recordOrder(key);
        }
      }
    }
    const live = asText(state.current_lesson);
    if (live) {
      const key = `l:${m}:${t}`;
      if (!teacherByKey.has(key)) {
        teacherByKey.set(key, live);
        recordOrder(key);
      }
    }
  }

  const turns: Turn[] = order.map((key) => {
    const [kind, mStr, tStr] = key.split(":");
    const m = Number(mStr);
    const t = Number(tStr);
    if (kind === "q") {
      return {
        kind: "students",
        key,
        module_index: m,
        timestep: t,
        moduleTitle: moduleTitle(moduleList, m),
        questions: questionsByKey.get(key) ?? [],
      };
    }
    return {
      kind: "teacher",
      key,
      module_index: m,
      timestep: t,
      phaseLabel: PHASE_LABELS[t] ?? `Step ${t}`,
      moduleTitle: moduleTitle(moduleList, m),
      lesson: teacherByKey.get(key) ?? "",
    };
  });

  if (turns.length === 0) {
    return (
      <div
        className={
          className ??
          "rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-sm text-slate-500"
        }
      >
        Class chat will appear once the teacher begins delivering.
      </div>
    );
  }

  return (
    <div
      className={
        className ?? "rounded-2xl border border-slate-200 bg-white shadow-sm"
      }
    >
      <div className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white px-5 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
          Class chat
        </p>
        <h3 className="text-sm font-semibold text-slate-900">
          Teacher delivery + student questions
        </h3>
        <p className="mt-0.5 text-[11px] text-slate-500">
          Full transparent feed of every teacher generation and student
          question, in order.
        </p>
      </div>
      <ol className="divide-y divide-slate-100">
        {turns.map((turn) => {
          if (turn.kind === "teacher") {
            return (
              <li key={turn.key} className="px-5 py-4">
                <div className="flex items-baseline justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[#1DA1F2]/10 text-[10px] font-semibold uppercase text-[#1B8CD8]">
                      T
                    </span>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-[#1DA1F2]">
                      Teacher · {turn.phaseLabel}
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                    M{turn.module_index + 1} · Step {turn.timestep}/5
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  {turn.moduleTitle}
                </p>
                <div className="mt-3 rounded-2xl border border-sky-100 bg-sky-50/40 px-4 py-3">
                  <Markdown text={turn.lesson} />
                </div>
              </li>
            );
          }

          return (
            <li key={turn.key} className="px-5 py-4">
              <div className="flex items-baseline justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-violet-100 text-[10px] font-semibold uppercase text-violet-700">
                    Q
                  </span>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-600">
                    Students asked
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                  M{turn.module_index + 1} · Q&amp;A
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">
                {turn.moduleTitle}
              </p>
              <ul className="mt-3 space-y-2">
                {turn.questions.map((q, i) => (
                  <li
                    key={`${q.student_id}-${i}`}
                    className="rounded-2xl border border-violet-100 bg-violet-50/40 px-4 py-2 text-sm text-slate-800"
                  >
                    <p className="text-[11px] font-semibold text-violet-700">
                      {q.name}
                    </p>
                    <p className="mt-0.5 leading-snug">{q.question}</p>
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
