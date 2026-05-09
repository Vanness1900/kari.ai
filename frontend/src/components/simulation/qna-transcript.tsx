"use client";

import type { ClassroomState } from "@/lib/api";

export function QnaTranscript({ state }: { state: ClassroomState | null }) {
  const questions = state?.qna_student_questions ?? [];
  const isQna = state?.current_timestep === 2;
  if (questions.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-sm text-slate-500">
        {isQna
          ? "Students preparing questions…"
          : "Q&A starts at timestep 2 of each module."}
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 bg-gradient-to-r from-violet-50 to-white px-5 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-600">
          Student Q&A · Module {state ? state.current_module + 1 : ""}
        </p>
        <h3 className="text-sm font-semibold text-slate-900">
          {questions.length} question{questions.length === 1 ? "" : "s"} on the floor
        </h3>
      </div>
      <ul className="divide-y divide-slate-100">
        {questions.map((q, i) => (
          <li key={`${q.student_id}-${i}`} className="flex gap-3 px-5 py-3">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-[11px] font-semibold text-violet-700">
              {q.name.slice(0, 2).toUpperCase()}
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-700">{q.name}</p>
              <p className="text-sm leading-snug text-slate-800">{q.question}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
