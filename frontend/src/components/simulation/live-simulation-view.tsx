"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useSimulationLive } from "@/lib/use-simulation-live";
import { ConfusionHeatmap } from "./confusion-heatmap";
import { KnowledgeGrowthChart } from "./knowledge-growth-chart";
import { QnaTranscript } from "./qna-transcript";
import { StudentGrid } from "./student-grid";
import { StudentTimeline } from "./student-timeline";
import { TeacherPanel } from "./teacher-panel";
import { TeachingQnaTimeline } from "./teaching-qna-timeline";

const PHASE_LABELS: Record<number, string> = {
  1: "Delivering",
  2: "Q&A",
  3: "Exercise",
  4: "Assessment",
  5: "Recap",
};

export function LiveSimulationView({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const { status, events, state, error } = useSimulationLive(sessionId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [autoRedirect, setAutoRedirect] = useState(true);

  useEffect(() => {
    if (autoRedirect && status?.simulation_complete) {
      const t = setTimeout(() => {
        router.push(`/report/${sessionId}`);
      }, 800);
      return () => clearTimeout(t);
    }
  }, [autoRedirect, status?.simulation_complete, router, sessionId]);

  const students = state?.students ?? [];
  const modules = state?.curriculum.modules ?? [];

  const selected = useMemo(
    () => students.find((s) => s.id === selectedId) ?? null,
    [students, selectedId],
  );

  const totalSteps = (modules.length || 1) * 5;
  const completedSteps =
    state == null
      ? 0
      : Math.min(totalSteps, (state.current_module ?? 0) * 5 + (state.current_timestep ?? 1) - 1);
  const progress = Math.round((completedSteps / Math.max(1, totalSteps)) * 100);
  const phaseLabel = state ? PHASE_LABELS[state.current_timestep] ?? `Step ${state.current_timestep}` : "Booting…";

  return (
    <div className="relative flex min-h-screen flex-col bg-gradient-to-b from-sky-50 via-white to-white">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#1DA1F2]">
              {state?.simulation_complete ? "Simulation complete" : phaseLabel}
            </p>
            <h1 className="truncate text-base font-semibold text-slate-900">
              {state?.curriculum.title ?? "Classroom simulation"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden h-2 w-44 overflow-hidden rounded-full bg-slate-100 sm:block">
              <div
                className="h-full bg-[#1DA1F2] transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs tabular-nums text-slate-500">
              {state ? `${completedSteps}/${totalSteps}` : "—"}
            </span>
            <button
              type="button"
              onClick={() => router.push(`/report/${sessionId}`)}
              disabled={!status?.simulation_complete}
              className="rounded-full bg-[#1DA1F2] px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition disabled:bg-slate-200 disabled:text-slate-500"
            >
              {status?.simulation_complete ? "Open report" : "Awaiting report…"}
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="mx-auto mt-3 w-full max-w-7xl px-4 sm:px-6">
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
            Polling hiccup: {error}
          </div>
        </div>
      )}
      {state?.simulation_error && (
        <div className="mx-auto mt-3 w-full max-w-7xl px-4 sm:px-6">
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs text-rose-800">
            Simulation error: {state.simulation_error}
          </div>
        </div>
      )}

      <main className="mx-auto grid w-full max-w-7xl flex-1 gap-4 px-4 py-6 sm:px-6 lg:grid-cols-[2fr_3fr]">
        <section className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Class
                </p>
                <h2 className="text-sm font-semibold text-slate-900">
                  {students.length} students · click to inspect
                </h2>
              </div>
              <span className="text-[11px] text-slate-500">
                avg confusion {state?.avg_confusion_last != null ? `${Math.round((state.avg_confusion_last) * 100)}%` : "—"}
              </span>
            </div>
            <StudentGrid
              students={students}
              events={events}
              onSelect={setSelectedId}
              selectedId={selectedId}
            />
          </div>
          <QnaTranscript state={state} />
          <TeachingQnaTimeline state={state} modules={modules} events={events} />
        </section>

        <section className="flex h-[80vh] min-h-[640px] flex-col">
          <TeacherPanel state={state} />
        </section>
      </main>

      <section className="mx-auto grid w-full max-w-7xl gap-4 px-4 pb-10 sm:px-6 lg:grid-cols-2">
        <KnowledgeGrowthChart students={students} events={events} />
        <ConfusionHeatmap students={students} modules={modules} events={events} />
      </section>

      {selected && (
        <StudentTimeline
          student={selected}
          events={events}
          onClose={() => setSelectedId(null)}
        />
      )}

      {status?.simulation_complete && autoRedirect && (
        <div className="pointer-events-auto fixed bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-slate-200 bg-white/95 px-4 py-2 text-xs text-slate-600 shadow-lg">
          Redirecting to report…{" "}
          <button
            type="button"
            onClick={() => setAutoRedirect(false)}
            className="ml-1 font-semibold text-[#1DA1F2] hover:underline"
          >
            Stay here
          </button>
        </div>
      )}
    </div>
  );
}
