"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StudentProfile, TimestepLog } from "@/lib/api";

const COLORS = [
  "#1DA1F2",
  "#7c3aed",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#0ea5e9",
  "#a855f7",
  "#14b8a6",
  "#f97316",
  "#6366f1",
];

type Row = { tick: number; label: string; [studentName: string]: number | string };

/**
 * Build a tick-by-tick mastery series. Each "tick" = one observed student log row, indexed
 * by module*10+timestep so QNA appears between deliver and exercise.
 */
function buildSeries(
  students: StudentProfile[],
  events: TimestepLog[],
): { rows: Row[]; ids: { id: string; name: string }[] } {
  const ids = students.map((s) => ({ id: s.id, name: s.name }));
  const lastByStudent: Record<string, number> = {};
  for (const s of students) {
    const ks = s.knowledge_state ?? {};
    const vals = Object.values(ks).filter((v): v is number => typeof v === "number");
    lastByStudent[s.id] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }
  // Group student-log events by (module, timestep) ordered.
  const phases = new Map<string, { mod: number; step: number; logs: TimestepLog[] }>();
  for (const e of events) {
    if (e.agent !== "student") continue;
    const key = `${e.module_index}:${e.timestep}`;
    const bucket = phases.get(key) ?? { mod: e.module_index, step: e.timestep, logs: [] };
    bucket.logs.push(e);
    phases.set(key, bucket);
  }
  const ordered = Array.from(phases.values()).sort(
    (a, b) => a.mod - b.mod || a.step - b.step,
  );

  // Initial (tick 0) — all baseline.
  const rows: Row[] = [];
  const baseline: Row = { tick: 0, label: "start" };
  for (const { id, name } of ids) baseline[name] = lastByStudent[id] ?? 0;
  rows.push(baseline);

  ordered.forEach(({ mod, step, logs }, idx) => {
    for (const log of logs) {
      const p = log.payload as { student_id?: string; knowledge_mastery_avg?: number };
      if (typeof p.student_id !== "string") continue;
      if (typeof p.knowledge_mastery_avg === "number") {
        lastByStudent[p.student_id] = p.knowledge_mastery_avg;
      }
    }
    const row: Row = { tick: idx + 1, label: `M${mod + 1}.${step}` };
    for (const { id, name } of ids) row[name] = lastByStudent[id] ?? 0;
    rows.push(row);
  });
  return { rows, ids };
}

export function KnowledgeGrowthChart({
  students,
  events,
}: {
  students: StudentProfile[];
  events: TimestepLog[];
}) {
  const { rows, ids } = buildSeries(students, events);
  if (ids.length === 0) {
    return <p className="text-sm text-slate-500">No students yet.</p>;
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-600">
          Mastery over time
        </p>
        <h3 className="text-sm font-semibold text-slate-900">Knowledge growth per student</h3>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "#64748b" }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => `${Math.round((v as number) * 100)}%`}
              tick={{ fontSize: 11, fill: "#64748b" }}
              width={42}
            />
            <Tooltip
              formatter={(value) =>
                typeof value === "number"
                  ? `${Math.round(value * 100)}%`
                  : String(value ?? "")
              }
              labelFormatter={(label) => `Phase ${label}`}
              contentStyle={{ fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {ids.map((s, i) => (
              <Line
                key={s.id}
                type="monotone"
                dataKey={s.name}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
