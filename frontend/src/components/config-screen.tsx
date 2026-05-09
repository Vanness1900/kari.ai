"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import {
  type CurriculumConfig,
  saveConfig,
} from "@/lib/config-storage";

const BLOOM_PRESETS = [
  "Remember",
  "Understand",
  "Apply",
  "Analyze",
  "Evaluate",
  "Create",
];

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function ConfigScreen() {
  const router = useRouter();
  const [curriculum, setCurriculum] = useState("");
  const [content, setContent] = useState("");
  const [bloomDraft, setBloomDraft] = useState("");
  const [bloomLevels, setBloomLevels] = useState<string[]>([]);
  const [durationWeeks, setDurationWeeks] = useState(12);
  const [classRatePerWeek, setClassRatePerWeek] = useState(4);
  const [totalStudents, setTotalStudents] = useState(20);

  const addBloomFromDraft = useCallback(() => {
    const v = bloomDraft.trim();
    if (!v) return;
    if (!bloomLevels.includes(v)) {
      setBloomLevels((prev) => [...prev, v]);
    }
    setBloomDraft("");
  }, [bloomDraft, bloomLevels]);

  const addBloomPreset = useCallback((level: string) => {
    setBloomLevels((prev) =>
      prev.includes(level) ? prev : [...prev, level],
    );
  }, []);

  const handleGenerate = () => {
    const config: CurriculumConfig = {
      curriculum: curriculum.trim(),
      content: content.trim(),
      bloomLevels,
      durationWeeks,
      classRatePerWeek,
      totalStudents,
    };
    saveConfig(config);
    router.push("/main");
  };

  return (
    <div className="relative min-h-full flex-1 overflow-hidden bg-gradient-to-b from-sky-50 via-white to-white">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 10%, rgba(29,161,242,0.18) 0%, transparent 45%), radial-gradient(circle at 80% 0%, rgba(29,161,242,0.12) 0%, transparent 40%)",
        }}
      />
      <div className="relative mx-auto flex min-h-full max-w-lg flex-col justify-center px-4 py-12 sm:px-6">
        <header className="mb-8 text-center">
          <p className="text-sm font-medium tracking-wide text-[#1DA1F2]">
            Kari
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Curriculum studio
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Shape your outline, then run it through a simulated class and
            teaching staff.
          </p>
        </header>

        <div className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-xl shadow-sky-100/60 backdrop-blur-sm sm:p-8">
          <div className="space-y-6">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Curriculum
              </span>
              <div className="flex gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 transition-colors focus-within:border-[#1DA1F2]/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1DA1F2]/20">
                <input
                  className="min-w-0 flex-1 bg-transparent text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder="e.g. Intro to data literacy"
                  value={curriculum}
                  onChange={(e) => setCurriculum(e.target.value)}
                />
                <button
                  type="button"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-[#1DA1F2]"
                  aria-label="Expand curriculum details"
                >
                  <PlusIcon />
                </button>
              </div>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Content
              </span>
              <div className="flex gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 transition-colors focus-within:border-[#1DA1F2]/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1DA1F2]/20">
                <textarea
                  rows={3}
                  className="min-h-[88px] w-full flex-1 resize-y bg-transparent text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder="Topics, modules, learning goals…"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
                <button
                  type="button"
                  className="mt-1 flex h-9 w-9 shrink-0 items-start justify-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-[#1DA1F2]"
                  aria-label="Add content block"
                >
                  <PlusIcon />
                </button>
              </div>
            </label>

            <div>
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Bloom level
              </span>
              <div className="flex gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 transition-colors focus-within:border-[#1DA1F2]/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1DA1F2]/20">
                <input
                  className="min-w-0 flex-1 bg-transparent text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder="Type a level, then add"
                  value={bloomDraft}
                  onChange={(e) => setBloomDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addBloomFromDraft();
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={addBloomFromDraft}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-[#1DA1F2]"
                  aria-label="Add Bloom level"
                >
                  <PlusIcon />
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {BLOOM_PRESETS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => addBloomPreset(p)}
                    className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-[#1DA1F2]/40 hover:text-[#1B8CD8]"
                  >
                    + {p}
                  </button>
                ))}
              </div>
              {bloomLevels.length > 0 && (
                <ul className="mt-3 flex flex-wrap gap-2">
                  {bloomLevels.map((b) => (
                    <li
                      key={b}
                      className="inline-flex items-center gap-1 rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-900"
                    >
                      {b}
                      <button
                        type="button"
                        className="ml-0.5 rounded-full p-0.5 text-sky-700 hover:bg-sky-200/80"
                        onClick={() =>
                          setBloomLevels((prev) => prev.filter((x) => x !== b))
                        }
                        aria-label={`Remove ${b}`}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <SliderField
              label="Duration"
              value={durationWeeks}
              min={4}
              max={24}
              step={1}
              formatValue={(v) => `${v} weeks`}
              onChange={setDurationWeeks}
            />
            <SliderField
              label="Class rate"
              value={classRatePerWeek}
              min={1}
              max={7}
              step={1}
              formatValue={(v) => `${v}/week`}
              onChange={setClassRatePerWeek}
            />
            <SliderField
              label="Total students"
              value={totalStudents}
              min={5}
              max={100}
              step={1}
              formatValue={(v) => String(v)}
              onChange={setTotalStudents}
            />
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            className="mt-8 w-full rounded-2xl bg-[#1DA1F2] py-3.5 text-base font-semibold text-white shadow-lg shadow-sky-300/50 transition hover:bg-[#1B8CD8] active:scale-[0.99]"
          >
            Generate
          </button>
        </div>

        <p className="mt-6 text-center text-xs text-slate-500">
          Front-end preview — connect your swarm API when you are ready.
        </p>
      </div>
    </div>
  );
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  formatValue,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  formatValue: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-[#1DA1F2]">
          {formatValue(value)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-[#1DA1F2] [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#1DA1F2] [&::-webkit-slider-thumb]:shadow [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-[#1DA1F2]"
      />
    </div>
  );
}
