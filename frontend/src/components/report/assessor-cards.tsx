"use client";

import type { AssessmentRecord, StudentProfile } from "@/lib/api";

function scoreTone(score: number): { ring: string; pill: string; bar: string } {
  if (score >= 0.75) return { ring: "ring-emerald-200", pill: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-500" };
  if (score >= 0.5) return { ring: "ring-amber-200", pill: "bg-amber-100 text-amber-700", bar: "bg-amber-500" };
  return { ring: "ring-rose-200", pill: "bg-rose-100 text-rose-700", bar: "bg-rose-500" };
}

export function AssessorCards({
  students,
  assessments,
}: {
  students: StudentProfile[];
  assessments: Record<string, AssessmentRecord>;
}) {
  const rows = students.map((s) => ({
    student: s,
    record: assessments[s.id] ?? null,
  }));
  if (rows.length === 0) {
    return null;
  }
  return (
    <div className="space-y-3">
      {rows.map(({ student, record }) => {
        const score = record?.overall_score ?? 0;
        const tone = scoreTone(score);
        return (
          <article
            key={student.id}
            className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ring-1 ${tone.ring}`}
          >
            <header className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h4 className="truncate text-sm font-semibold text-slate-900">
                  {student.name}
                </h4>
                <p className="text-[11px] text-slate-500">
                  {student.learning_style ?? ""} · attention span {student.attention_span_mins ?? "—"}m
                </p>
              </div>
              <div className="flex items-center gap-2">
                {record?.risk_flags?.map((f) => (
                  <span
                    key={f}
                    className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-medium text-rose-700"
                  >
                    {f.replace(/_/g, " ")}
                  </span>
                ))}
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tone.pill}`}>
                  {Math.round(score * 100)}%
                </span>
              </div>
            </header>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div className={`h-full ${tone.bar}`} style={{ width: `${Math.round(score * 100)}%` }} />
            </div>
            {record?.narrative ? (
              <p className="mt-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-700">
                {record.narrative}
              </p>
            ) : (
              <p className="mt-3 text-xs italic text-slate-400">No narrative recorded.</p>
            )}
          </article>
        );
      })}
    </div>
  );
}
