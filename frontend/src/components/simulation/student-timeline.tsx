"use client";

import type { StudentProfile, TimestepLog } from "@/lib/api";

const PHASE_LABELS: Record<number, string> = {
  1: "Deliver",
  2: "Q&A",
  3: "Exercise",
  4: "Assessment",
  5: "Recap",
};

export function StudentTimeline({
  student,
  events,
  onClose,
}: {
  student: StudentProfile;
  events: TimestepLog[];
  onClose: () => void;
}) {
  const rows = events.filter(
    (e) =>
      e.agent === "student" &&
      (e.payload as { student_id?: string }).student_id === student.id,
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-slate-900/40 sm:items-center sm:justify-center">
      <div className="flex h-[80vh] w-full max-w-xl flex-col rounded-t-3xl border border-slate-200 bg-white shadow-2xl sm:h-[70vh] sm:rounded-3xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Student timeline
            </p>
            <h3 className="text-base font-semibold text-slate-900">{student.name}</h3>
            <p className="text-[11px] text-slate-500">
              {student.learning_style ?? ""} · attention {Math.round((student.attention_remaining ?? 1) * 100)}% · confusion {Math.round((student.confusion_level ?? 0) * 100)}%
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
            aria-label="Close timeline"
          >
            ×
          </button>
        </div>
        <div className="grow overflow-auto px-5 py-3">
          {rows.length === 0 ? (
            <p className="text-sm text-slate-500">No events for this student yet.</p>
          ) : (
            <ol className="space-y-2">
              {rows.map((e, i) => {
                const p = e.payload as {
                  confusion_level?: number;
                  attention_remaining?: number;
                  knowledge_mastery_avg?: number;
                  knowledge_delta?: number;
                  action?: string;
                  understood?: boolean;
                };
                const conf = Math.round((p.confusion_level ?? 0) * 100);
                const mastery = Math.round((p.knowledge_mastery_avg ?? 0) * 100);
                const delta = p.knowledge_delta ?? 0;
                const phase = PHASE_LABELS[e.timestep] ?? `Step ${e.timestep}`;
                return (
                  <li
                    key={i}
                    className="rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-700">
                        Module {e.module_index + 1} · {phase}
                      </span>
                      <span className="text-slate-500">
                        {p.action ? p.action.replace(/_/g, " ") : ""}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-slate-600">
                      <span>Confusion {conf}%</span>
                      <span>Mastery {mastery}%</span>
                      <span className={delta > 0 ? "text-emerald-600" : delta < 0 ? "text-rose-600" : ""}>
                        Δ {delta > 0 ? "+" : ""}
                        {delta.toFixed(2)}
                      </span>
                      {p.understood !== undefined && (
                        <span className={p.understood ? "text-emerald-600" : "text-amber-600"}>
                          {p.understood ? "understood" : "lost"}
                        </span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
