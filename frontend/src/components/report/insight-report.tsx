"use client";

import type { InsightReport } from "@/lib/api";

/**
 * Insight agent currently returns free-text. Render it as a readable column with
 * a few light heuristics so headings and lists from markdown-y output still surface.
 */
export function InsightReportView({ report }: { report: InsightReport | null }) {
  if (!report) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
        Insight report not available.
      </div>
    );
  }
  const text = (report.curriculum_critique || report.summary || "").trim();
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-white px-5 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-600">
          Insight agent
        </p>
        <h3 className="text-sm font-semibold text-slate-900">Curriculum critique</h3>
      </div>
      <div className="space-y-3 px-5 py-4 text-sm leading-relaxed text-slate-800">
        {text.split(/\n{2,}/).map((para, i) => (
          <p key={i} className="whitespace-pre-wrap">
            {para}
          </p>
        ))}
        {report.blooms_alignment_notes && report.blooms_alignment_notes.length > 0 && (
          <div className="mt-3 rounded-xl border border-slate-100 bg-slate-50 p-3">
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Bloom alignment notes
            </p>
            <ul className="list-disc space-y-1 pl-5 text-xs text-slate-700">
              {report.blooms_alignment_notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
