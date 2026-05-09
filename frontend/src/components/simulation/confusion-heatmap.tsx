"use client";

import type { CurriculumModule, StudentProfile, TimestepLog } from "@/lib/api";

/**
 * Per-student × per-module average confusion. Built from `timestep_logs` entries
 * where agent="student" — those carry `confusion_level` per student per phase.
 */
function buildMatrix(
  students: StudentProfile[],
  modules: CurriculumModule[],
  events: TimestepLog[],
): number[][] {
  const matrix: number[][] = students.map(() => modules.map(() => Number.NaN));
  const sums: number[][] = students.map(() => modules.map(() => 0));
  const counts: number[][] = students.map(() => modules.map(() => 0));
  const idIndex = new Map(students.map((s, i) => [s.id, i]));

  for (const e of events) {
    if (e.agent !== "student") continue;
    const p = e.payload as { student_id?: string; confusion_level?: number };
    if (typeof p.student_id !== "string" || typeof p.confusion_level !== "number") continue;
    const si = idIndex.get(p.student_id);
    const mi = e.module_index;
    if (si === undefined || mi < 0 || mi >= modules.length) continue;
    sums[si][mi] += p.confusion_level;
    counts[si][mi] += 1;
  }
  for (let s = 0; s < students.length; s++) {
    for (let m = 0; m < modules.length; m++) {
      matrix[s][m] = counts[s][m] > 0 ? sums[s][m] / counts[s][m] : Number.NaN;
    }
  }
  return matrix;
}

function cellClass(level: number): string {
  if (Number.isNaN(level)) return "bg-slate-50";
  if (level >= 0.75) return "bg-rose-500/90 text-white";
  if (level >= 0.6) return "bg-rose-400/90 text-white";
  if (level >= 0.45) return "bg-amber-400/90 text-amber-950";
  if (level >= 0.3) return "bg-amber-200 text-amber-900";
  if (level >= 0.15) return "bg-emerald-200 text-emerald-900";
  return "bg-emerald-100 text-emerald-900";
}

export function ConfusionHeatmap({
  students,
  modules,
  events,
}: {
  students: StudentProfile[];
  modules: CurriculumModule[];
  events: TimestepLog[];
}) {
  if (students.length === 0 || modules.length === 0) {
    return null;
  }
  const matrix = buildMatrix(students, modules, events);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-600">
          Confusion heatmap
        </p>
        <h3 className="text-sm font-semibold text-slate-900">Where the class struggles</h3>
      </div>
      <div className="overflow-auto">
        <table className="w-full border-separate border-spacing-1 text-xs">
          <thead>
            <tr>
              <th className="sticky left-0 bg-white pr-2 text-left text-[11px] font-medium text-slate-500">
                Student
              </th>
              {modules.map((m, i) => (
                <th
                  key={m.id ?? i}
                  className="px-1 text-center text-[11px] font-medium text-slate-500"
                  title={m.title}
                >
                  M{i + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map((s, si) => (
              <tr key={s.id}>
                <td className="sticky left-0 bg-white pr-2 text-[11px] font-medium text-slate-700">
                  {s.name}
                </td>
                {modules.map((m, mi) => {
                  const v = matrix[si][mi];
                  return (
                    <td
                      key={m.id ?? mi}
                      className={`h-7 min-w-[2.25rem] rounded-md text-center text-[11px] font-semibold tabular-nums ${cellClass(v)}`}
                      title={
                        Number.isNaN(v)
                          ? "no data yet"
                          : `Confusion: ${Math.round(v * 100)}%`
                      }
                    >
                      {Number.isNaN(v) ? "·" : Math.round(v * 100)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
