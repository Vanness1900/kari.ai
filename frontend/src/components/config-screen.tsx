"use client";

import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import {
  type CurriculumConfig,
  saveConfig,
} from "@/lib/config-storage";
import {
  LS_IMPORT_CONTENT,
  LS_IMPORT_CURRICULUM,
  readFileAsDataUrl,
  readImportedFiles,
  truncateFileLabel,
  type LocalImportBucket,
  type LocalImportedFile,
  writeImportedFiles,
} from "@/lib/local-import-storage";

const ACCEPT_IMPORT =
  "application/pdf,.pdf,image/jpeg,image/png,image/webp,image/gif";

/** Some OS pickers omit `file.type` for PDF/images — fall back on extension */
function inferredMime(file: File): string {
  if (file.type) return file.type;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "pdf") return "application/pdf";
  if (ext === "jpg" || ext === "jpeg") return "image/jpeg";
  if (ext === "png") return "image/png";
  if (ext === "gif") return "image/gif";
  if (ext === "webp") return "image/webp";
  return "";
}

function acceptsImportFile(file: File): boolean {
  const mime = inferredMime(file);
  return mime === "application/pdf" || mime.startsWith("image/");
}

const BLOOM_PRESETS = [
  "Remember",
  "Understand",
  "Apply",
  "Analyze",
  "Evaluate",
  "Create",
];

const VISION_MISSION_TEMPLATES: { id: string; label: string; text: string }[] = [
  {
    id: "access-transformation",
    label: "Access, equity & social impact",
    text: "Vision: Education that widens access and reduces barriers so more people can participate and thrive.\nMission: Design learning experiences that are inclusive, culturally responsive, and focused on real-world impact for communities that have been underserved.",
  },
  {
    id: "career-ready",
    label: "Career-ready & industry aligned",
    text: "Vision: Graduates leave with skills and judgment they can apply on day one in professional settings.\nMission: Align outcomes to industry needs, emphasize practice over theory alone, and validate learning through authentic tasks and feedback.",
  },
  {
    id: "critical-thinking",
    label: "Critical thinking & informed citizenship",
    text: "Vision: Learners think clearly, question assumptions, and act responsibly with information.\nMission: Build habits of evidence-based reasoning, constructive debate, and ethical decision-making across contexts.",
  },
  {
    id: "lifelong-learning",
    label: "Lifelong learning & adaptability",
    text: "Vision: Learners keep growing after the course ends in a fast-changing world.\nMission: Teach how to learn independently, surface meta-cognitive strategies, and connect content to future self-study and professional change.",
  },
  {
    id: "research-innovation",
    label: "Discovery, research & innovation",
    text: "Vision: Learners contribute to new knowledge, creative work, or technical innovation.\nMission: Emphasize inquiry, experimentation, peer review, iteration, and rigorous standards for claims and methods.",
  },
  {
    id: "wellbeing-holistic",
    label: "Well-being & holistic development",
    text: "Vision: Learning supports the whole person—not only grades or output.\nMission: Balance challenge with support, embed reflection, collaboration, and habits that sustain motivation, health, and confidence.",
  },
];

const DURATION_WEEKS_MIN = 1;
const DURATION_WEEKS_MAX = 48;

/** Weeks 1–11 in steps of 1; from 12 onward in steps of 4 through `DURATION_WEEKS_MAX`. */
function snapDurationWeeks(raw: number): number {
  const n = Math.max(
    DURATION_WEEKS_MIN,
    Math.min(DURATION_WEEKS_MAX, Math.round(raw)),
  );
  if (n < 12) return n;
  const k = Math.round((n - 12) / 4);
  return Math.min(
    DURATION_WEEKS_MAX,
    Math.max(12, 12 + k * 4),
  );
}

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

function ChevronDownIcon({ className }: { className?: string }) {
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
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function ChevronUpIcon({ className }: { className?: string }) {
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
      <path d="m18 15-6-6-6 6" />
    </svg>
  );
}

function ImportedAttachmentCard({
  file,
  onRemove,
}: {
  file: LocalImportedFile;
  onRemove: () => void;
}) {
  const isPdf =
    file.mimeType === "application/pdf" ||
    file.name.toLowerCase().endsWith(".pdf");
  const isImage = file.mimeType.startsWith("image/");
  const label = truncateFileLabel(file.name);

  return (
    <div className="relative w-[5.75rem] shrink-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${file.name}`}
        className="absolute right-1 top-1 z-10 flex h-5 w-5 items-center justify-center rounded-full border border-slate-200/90 bg-white/95 text-[11px] leading-none font-semibold text-slate-600 shadow-sm transition hover:bg-rose-50 hover:text-rose-600"
      >
        ×
      </button>

      <div className="relative aspect-[5/7] bg-slate-100">
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element -- data URLs from local uploads
          <img
            src={file.dataUrl}
            alt=""
            className="h-full w-full object-cover object-center"
          />
        ) : isPdf ? (
          <div className="relative flex h-full flex-col bg-gradient-to-br from-slate-100 via-slate-50 to-slate-200 pt-4">
            <div className="mx-2 mb-3 flex flex-1 flex-col gap-0.5 px-2">
              <div className="h-1 rounded bg-slate-300/70" />
              <div className="h-1 w-5/6 rounded bg-slate-300/55" />
              <div className="h-1 w-11/12 rounded bg-slate-300/55" />
              <div className="h-1 w-4/6 rounded bg-slate-300/55" />
            </div>
            <span className="absolute bottom-2 left-2 rounded-md border border-slate-200/80 bg-white px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-slate-700 shadow-sm">
              PDF
            </span>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center bg-slate-100 text-[10px] text-slate-500">
            File
          </div>
        )}
      </div>

      <p
        className="truncate px-2 py-1.5 text-center text-[11px] font-medium text-slate-700"
        title={file.name}
      >
        {label}
      </p>
    </div>
  );
}

export function ConfigScreen() {
  const router = useRouter();
  const [sessionName, setSessionName] = useState("");
  const [curriculum, setCurriculum] = useState("");
  const [content, setContent] = useState("");
  const [curriculumImports, setCurriculumImports] = useState<LocalImportedFile[]>(
    [],
  );
  const [contentImports, setContentImports] = useState<LocalImportedFile[]>([]);
  const curriculumInputRef = useRef<HTMLInputElement>(null);
  const contentInputRef = useRef<HTMLInputElement>(null);

  const [selectedBloom, setSelectedBloom] = useState<string>("");
  const [bloomMenuOpen, setBloomMenuOpen] = useState(false);
  const bloomMenuRef = useRef<HTMLDivElement>(null);
  const [durationWeeks, setDurationWeeks] = useState(12);
  const [classRatePerWeek, setClassRatePerWeek] = useState(4);
  const [totalStudents, setTotalStudents] = useState(20);

  const [visionMissionPreset, setVisionMissionPreset] = useState("");
  const [visionMissionText, setVisionMissionText] = useState("");
  const [targetStudentsDescription, setTargetStudentsDescription] = useState("");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate from localStorage after mount
    setCurriculumImports(readImportedFiles(LS_IMPORT_CURRICULUM));
    setContentImports(readImportedFiles(LS_IMPORT_CONTENT));
  }, []);

  const processFileListAppend = async (
    bucket: LocalImportBucket,
    files: File[],
    setter: Dispatch<SetStateAction<LocalImportedFile[]>>,
  ) => {
    if (!files.length) return;
    const incoming: LocalImportedFile[] = [];
    for (const file of files) {
      if (!acceptsImportFile(file)) continue;
      const mimeForStore = inferredMime(file);
      try {
        const dataUrl = await readFileAsDataUrl(file);
        incoming.push({
          id:
            typeof crypto !== "undefined" && crypto.randomUUID
              ? crypto.randomUUID()
              : `f-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          name: file.name,
          mimeType: mimeForStore,
          dataUrl,
        });
      } catch {
        console.error("Could not read file", file.name);
      }
    }
    if (!incoming.length) return;
    setter((prev) => {
      const next = [...prev, ...incoming];
      try {
        writeImportedFiles(bucket, next);
        return next;
      } catch {
        alert(
          "Not enough browser storage for that file — try a smaller PDF or fewer imports.",
        );
        return prev;
      }
    });
  };

  useEffect(() => {
    if (!bloomMenuOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      const el = bloomMenuRef.current;
      if (el && !el.contains(e.target as Node)) {
        setBloomMenuOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [bloomMenuOpen]);

  const handleGenerate = () => {
    const visionMission = visionMissionText.trim();
    const targetStudents = targetStudentsDescription.trim();
    const config: CurriculumConfig = {
      sessionName: sessionName.trim(),
      curriculum: curriculum.trim(),
      content: content.trim(),
      ...(visionMission ? { visionMission } : {}),
      ...(targetStudents ? { targetStudentsDescription: targetStudents } : {}),
      bloomLevels: selectedBloom.trim() ? [selectedBloom.trim()] : [],
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
            Kuri.ai
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Curriculum studio
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Shape your outline, then run it through a simulated class and
            teaching staff. Get feedback on your curriculum and improve it.
          </p>
        </header>

        <div className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-xl shadow-sky-100/60 backdrop-blur-sm sm:p-8">
          <div className="space-y-6">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Session name
              </span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-[#1DA1F2]/50 focus:bg-white focus:ring-2 focus:ring-[#1DA1F2]/20"
                placeholder="Name this studio session"
                value={sessionName ?? ""}
                onChange={(e) => setSessionName(e.target.value)}
              />
            </label>

          <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Curriculum
              </span>
              <div className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 transition-colors focus-within:border-[#1DA1F2]/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1DA1F2]/20">
                <input
                  ref={curriculumInputRef}
                  type="file"
                  className="sr-only"
                  accept={ACCEPT_IMPORT}
                  multiple
                  aria-hidden
                  tabIndex={-1}
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    e.target.value = "";
                    void processFileListAppend(
                      LS_IMPORT_CURRICULUM,
                      files,
                      setCurriculumImports,
                    );
                  }}
                />
                {curriculumImports.length > 0 && (
                  <div className="flex gap-2 overflow-x-auto pb-1 pt-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                    {curriculumImports.map((f) => (
                      <ImportedAttachmentCard
                        key={f.id}
                        file={f}
                        onRemove={() => {
                          setCurriculumImports((prev) => {
                            const next = prev.filter((x) => x.id !== f.id);
                            writeImportedFiles(LS_IMPORT_CURRICULUM, next);
                            return next;
                          });
                        }}
                      />
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <textarea
                    rows={3}
                    className="min-h-[88px] w-full min-w-0 flex-1 resize-y bg-transparent text-slate-900 outline-none placeholder:text-slate-400"
                    placeholder="Paste or import your curriculum"
                    value={content ?? ""}
                    onChange={(e) => setContent(e.target.value)}
                  />
                  <button
                    type="button"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-[#1DA1F2]"
                    aria-label="Import PDF or image for curriculum"
                    onClick={() => curriculumInputRef.current?.click()}
                  >
                    <PlusIcon />
                  </button>
                </div>
              </div>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Content
              </span>
              <div className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 transition-colors focus-within:border-[#1DA1F2]/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1DA1F2]/20">
                <input
                  ref={contentInputRef}
                  type="file"
                  className="sr-only"
                  accept={ACCEPT_IMPORT}
                  multiple
                  aria-hidden
                  tabIndex={-1}
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    e.target.value = "";
                    void processFileListAppend(
                      LS_IMPORT_CONTENT,
                      files,
                      setContentImports,
                    );
                  }}
                />
                {contentImports.length > 0 && (
                  <div className="flex gap-2 overflow-x-auto pb-1 pt-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                    {contentImports.map((f) => (
                      <ImportedAttachmentCard
                        key={f.id}
                        file={f}
                        onRemove={() => {
                          setContentImports((prev) => {
                            const next = prev.filter((x) => x.id !== f.id);
                            writeImportedFiles(LS_IMPORT_CONTENT, next);
                            return next;
                          });
                        }}
                      />
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <input
                    className="min-w-0 flex-1 bg-transparent text-slate-900 outline-none placeholder:text-slate-400"
                    placeholder="Import related slides and notes"
                    value={curriculum ?? ""}
                    onChange={(e) => setCurriculum(e.target.value)}
                  />
                  <button
                    type="button"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-[#1DA1F2]"
                    aria-label="Import PDF or image for content"
                    onClick={() => contentInputRef.current?.click()}
                  >
                    <PlusIcon />
                  </button>
                </div>
              </div>
            </label>

            <div>
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Vision &amp; mission
              </span>
              <select
                className="mb-2 w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm text-slate-900 outline-none transition-colors focus:border-[#1DA1F2]/50 focus:bg-white focus:ring-2 focus:ring-[#1DA1F2]/20"
                aria-label="Vision and mission preset"
                value={visionMissionPreset}
                onChange={(e) => {
                  const id = e.target.value;
                  setVisionMissionPreset(id);
                  if (!id || id === "__custom__") return;
                  const t = VISION_MISSION_TEMPLATES.find((x) => x.id === id);
                  if (t) setVisionMissionText(t.text);
                }}
              >
                <option value="">
                  Pick a common vision/mission framing (optional)
                </option>
                {VISION_MISSION_TEMPLATES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
                <option value="__custom__">Write entirely my own (below)</option>
              </select>
              <textarea
                rows={4}
                className="w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-[#1DA1F2]/50 focus:bg-white focus:ring-2 focus:ring-[#1DA1F2]/20"
                placeholder="Edit the template above or write your vision and mission in full."
                value={visionMissionText ?? ""}
                onChange={(e) => setVisionMissionText(e.target.value)}
              />
            </div>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Target students
              </span>
              <textarea
                rows={4}
                className="w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-[#1DA1F2]/50 focus:bg-white focus:ring-2 focus:ring-[#1DA1F2]/20"
                placeholder="Describe who they are (roles, backgrounds, institution) and age range or typical cohort stage."
                value={targetStudentsDescription ?? ""}
                onChange={(e) => setTargetStudentsDescription(e.target.value)}
              />
            </label>
            
            <div>
              <span
                id="bloom-level-label"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Bloom level
              </span>
              <div ref={bloomMenuRef} className="relative">
                <button
                  type="button"
                  id="bloom-level-trigger"
                  aria-labelledby="bloom-level-label"
                  aria-expanded={bloomMenuOpen}
                  aria-haspopup="listbox"
                  onClick={() => setBloomMenuOpen((o) => !o)}
                  className={`flex w-full items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-left transition-colors ${
                    bloomMenuOpen
                      ? "border-[#1DA1F2]/50 bg-white ring-2 ring-[#1DA1F2]/20"
                      : ""
                  }`}
                >
                  <span
                    className={
                      selectedBloom ? "flex-1 text-slate-900" : "flex-1 text-slate-400"
                    }
                  >
                    {selectedBloom || "Choose a Bloom level"}
                  </span>
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-[#1DA1F2]"
                    aria-hidden
                  >
                    {bloomMenuOpen ? <ChevronUpIcon /> : <ChevronDownIcon />}
                  </span>
                </button>
                {bloomMenuOpen && (
                  <ul
                    role="listbox"
                    aria-labelledby="bloom-level-label"
                    className="absolute z-30 mt-1 max-h-60 w-full overflow-auto rounded-2xl border border-slate-200 bg-white py-1"
                  >
                    {selectedBloom ? (
                      <li role="presentation">
                        <button
                          type="button"
                          role="option"
                          aria-selected={false}
                          className="w-full px-3 py-2 text-left text-xs font-medium text-slate-500 transition hover:bg-slate-50"
                          onClick={() => {
                            setSelectedBloom("");
                            setBloomMenuOpen(false);
                          }}
                        >
                          Clear selection
                        </button>
                      </li>
                    ) : null}
                    {BLOOM_PRESETS.map((p) => (
                      <li key={p} role="presentation">
                        <button
                          type="button"
                          id={`bloom-option-${p}`}
                          role="option"
                          aria-selected={selectedBloom === p}
                          className={`w-full px-3 py-2 text-left text-sm transition ${
                            selectedBloom === p
                              ? "bg-sky-50 font-medium text-[#1B8CD8]"
                              : "text-slate-700 hover:bg-slate-50"
                          }`}
                          onClick={() => {
                            setSelectedBloom(p);
                            setBloomMenuOpen(false);
                          }}
                        >
                          {p}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <SliderField
              label="Duration"
              value={durationWeeks}
              min={DURATION_WEEKS_MIN}
              max={DURATION_WEEKS_MAX}
              step={1}
              formatValue={(v) => `${v} weeks`}
              onChange={(v) => setDurationWeeks(snapDurationWeeks(v))}
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
              max={50}
              step={5}
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
