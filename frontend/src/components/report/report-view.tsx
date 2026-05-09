"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ConfusionHeatmap } from "@/components/simulation/confusion-heatmap";
import { KnowledgeGrowthChart } from "@/components/simulation/knowledge-growth-chart";
import { type ReportResponse, getReport } from "@/lib/api";
import { AssessorCards } from "./assessor-cards";
import { InsightReportView } from "./insight-report";
import { TeachingQnaTimeline } from "@/components/simulation/teaching-qna-timeline";

export function ReportView({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const res = await getReport(sessionId);
        if (!cancel) setData(res);
      } catch (e) {
        if (!cancel) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancel = true;
    };
  }, [sessionId]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-12">
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          Could not load report: {error}
        </div>
        <Link
          href={`/simulation/${encodeURIComponent(sessionId)}`}
          className="mt-4 inline-block text-sm text-[#1DA1F2] hover:underline"
        >
          ← Back to live view
        </Link>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-12 text-sm text-slate-500">
        Loading report…
      </div>
    );
  }

  const modules = data.curriculum.modules ?? [];
  const assessments = data.student_assessments;
  const scores = Object.values(assessments).map((a) => a.overall_score);
  const avgScore =
    scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const atRisk = Object.values(assessments).filter(
    (a) => (a.risk_flags?.length ?? 0) > 0,
  ).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-white">
      <header className="border-b border-slate-200/80 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-600">
              Insight report
            </p>
            <h1 className="truncate text-lg font-semibold text-slate-900">
              {data.curriculum.title ?? "Untitled curriculum"}
            </h1>
            <p className="text-[11px] text-slate-500">Session {data.session_id}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/simulation/${encodeURIComponent(sessionId)}`}
              className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Replay live view
            </Link>
            <Link
              href="/"
              className="rounded-full bg-[#1DA1F2] px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-[#1B8CD8]"
            >
              New simulation
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-7xl gap-4 px-4 py-6 sm:px-6 lg:grid-cols-[1fr_1.4fr]">
        <section className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Stat
              label="Students"
              value={String(data.students.length)}
              tone="text-slate-900"
            />
            <Stat
              label="Avg score"
              value={`${Math.round(avgScore * 100)}%`}
              tone={avgScore >= 0.6 ? "text-emerald-600" : "text-amber-600"}
            />
            <Stat
              label="At risk"
              value={String(atRisk)}
              tone={atRisk > 0 ? "text-rose-600" : "text-emerald-600"}
            />
          </div>
          <InsightReportView report={data.insight_report} />
          <TeachingQnaTimeline
            state={null}
            modules={modules}
            events={data.timestep_logs}
          />
        </section>
        <section className="space-y-4">
          <KnowledgeGrowthChart students={data.students} events={data.timestep_logs} />
          <ConfusionHeatmap
            students={data.students}
            modules={modules}
            events={data.timestep_logs}
          />
        </section>
      </main>

      <section className="mx-auto w-full max-w-7xl px-4 pb-12 sm:px-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Per-student verdicts</h2>
        <AssessorCards students={data.students} assessments={assessments} />
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className={`text-xl font-semibold tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}
