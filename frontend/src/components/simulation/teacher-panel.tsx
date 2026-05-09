"use client";

import type { ClassroomState } from "@/lib/api";

const PHASE_LABELS: Record<number, string> = {
  1: "Deliver",
  2: "Q&A",
  3: "Exercise",
  4: "Assessment",
  5: "Recap",
};

export function TeacherPanel({ state }: { state: ClassroomState | null }) {
  if (!state) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
        Waiting for the teacher to begin…
      </div>
    );
  }
  const modules = state.curriculum.modules ?? [];
  const mod = modules[state.current_module];
  const phase = PHASE_LABELS[state.current_timestep] ?? `Step ${state.current_timestep}`;
  const lesson = state.current_lesson?.trim() || "";

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 bg-gradient-to-r from-sky-50 to-white px-5 py-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#1DA1F2]">
            Teacher · {phase}
          </p>
          <h3 className="truncate text-sm font-semibold text-slate-900">
            {mod?.title ?? `Module ${state.current_module + 1}`}
          </h3>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
          Module {state.current_module + 1}/{modules.length || 1} · Step {state.current_timestep}/5
        </span>
      </div>
      <div className="grow overflow-auto px-5 py-4">
        {lesson ? (
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-800">
            {lesson}
          </pre>
        ) : (
          <p className="text-sm text-slate-400">Generating lesson content…</p>
        )}
      </div>
    </div>
  );
}
