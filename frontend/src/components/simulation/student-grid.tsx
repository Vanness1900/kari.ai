"use client";

import type { StudentProfile, TimestepLog } from "@/lib/api";

function masteryAvg(s: StudentProfile): number {
  const ks = s.knowledge_state ?? {};
  const vals = Object.values(ks).filter((v): v is number => typeof v === "number");
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
}

function confusionTone(level: number): { bg: string; text: string; ring: string } {
  if (level >= 0.66) return { bg: "bg-rose-50", text: "text-rose-700", ring: "ring-rose-200" };
  if (level >= 0.33) return { bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-200" };
  return { bg: "bg-emerald-50", text: "text-emerald-700", ring: "ring-emerald-200" };
}

function lastAction(logs: TimestepLog[], studentId: string): string | null {
  for (let i = logs.length - 1; i >= 0; i--) {
    const l = logs[i];
    if (l.agent !== "student") continue;
    const p = l.payload as { student_id?: string; action?: string };
    if (p.student_id === studentId && typeof p.action === "string") return p.action;
  }
  return null;
}

export function StudentGrid({
  students,
  events,
  onSelect,
  selectedId,
}: {
  students: StudentProfile[];
  events: TimestepLog[];
  onSelect?: (id: string) => void;
  selectedId?: string | null;
}) {
  if (students.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
        Waiting for the class to take their seats…
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {students.map((s) => {
        const conf = s.confusion_level ?? 0;
        const attn = s.attention_remaining ?? 1;
        const mastery = masteryAvg(s);
        const tone = confusionTone(conf);
        const action = lastAction(events, s.id);
        const isSelected = selectedId === s.id;
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect?.(s.id)}
            className={`rounded-xl border bg-white p-3 text-left text-sm shadow-sm transition hover:shadow-md ${
              isSelected ? "border-[#1DA1F2] ring-2 ring-[#1DA1F2]/30" : "border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-semibold text-slate-900">{s.name}</span>
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ${tone.bg} ${tone.text} ${tone.ring}`}
              >
                {Math.round(conf * 100)}%
              </span>
            </div>
            <div className="mt-2 space-y-1.5">
              <Bar label="Attention" value={attn} colorClass="bg-sky-500" />
              <Bar label="Mastery" value={mastery} colorClass="bg-emerald-500" />
            </div>
            <p className="mt-2 truncate text-[11px] text-slate-500">
              {action ? `Last: ${action.replace(/_/g, " ")}` : s.learning_style ?? ""}
            </p>
          </button>
        );
      })}
    </div>
  );
}

function Bar({ label, value, colorClass }: { label: string; value: number; colorClass: string }) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div>
      <div className="mb-0.5 flex items-center justify-between text-[10px] text-slate-500">
        <span>{label}</span>
        <span className="tabular-nums">{Math.round(clamped * 100)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full ${colorClass}`} style={{ width: `${clamped * 100}%` }} />
      </div>
    </div>
  );
}
