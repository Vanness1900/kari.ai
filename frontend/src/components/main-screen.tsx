"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_SESSION_TITLE,
  clearConfig,
  loadConfig,
  type CurriculumConfig,
} from "@/lib/config-storage";
import {
  LS_IMPORT_CONTENT,
  LS_IMPORT_CURRICULUM,
} from "@/lib/local-import-storage";

type ChatRole = "user" | "ai" | "ai_card";

type ChatMessage = {
  id: string;
  role: ChatRole;
  title?: string;
  body: string;
};

function buildDemoTranscript(config: CurriculumConfig | null): ChatMessage[] {
  const title = config?.curriculum?.length
    ? config.curriculum
    : "your curriculum";
  return [
    {
      id: "1",
      role: "ai",
      title: "Teaching lead",
      body: `Synced ${config?.totalStudents ?? 20} simulated learners and staff for "${title}". I will coach pacing and assessments.`,
    },
    {
      id: "2",
      role: "user",
      body: "Please stress-check week 3 — it's dense for beginners.",
    },
    {
      id: "3",
      role: "ai",
      title: "Student cluster A",
      body: `We stalled on prerequisites when Bloom focus was heavy on Analyze/Evaluate (${(config?.bloomLevels ?? []).slice(0, 2).join(", ") || "higher tiers"}). Suggest one refresher micro-module.`,
    },
    {
      id: "4",
      role: "ai_card",
      title: "Swarm synthesis",
      body:
        "Here is how engagement trended across the run (illustrative). Your report panel shows the fuller breakdown with visuals.",
    },
    {
      id: "5",
      role: "user",
      body: `Timeline: ${config?.durationWeeks ?? 12} weeks at ${config?.classRatePerWeek ?? 4} sessions/week — does that leave room for projects?`,
    },
    {
      id: "6",
      role: "ai",
      title: "Teacher cohort",
      body: "Yes, if two weeks are labeled as consolidation. Otherwise swap one lecture for guided studio.",
    },
  ];
}

export function MainScreen() {
  const router = useRouter();
  /** undefined = have not read sessionStorage yet (SSR + first paint; avoid locking to null) */
  const [config, setConfig] = useState<
    CurriculumConfig | null | undefined
  >(undefined);
  const [draft, setDraft] = useState("");
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const didRedirectRef = useRef(false);

  useEffect(() => {
    const c = loadConfig();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load from sessionStorage after mount
    setConfig(c);
    if (!c && !didRedirectRef.current) {
      didRedirectRef.current = true;
      router.replace("/");
    }
  }, [router]);

  const messages = useMemo(() => buildDemoTranscript(config ?? null), [config]);

  const [extras, setExtras] = useState<ChatMessage[]>([]);

  useEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    /** Scroll inside the chat column only — scrollIntoView() walks ancestors and jittered the viewport */
    el.scrollTop = el.scrollHeight;
  }, [messages, extras]);

  if (config === undefined) {
    return (
      <div className="flex min-h-screen flex-1 items-center justify-center bg-slate-50 text-sm text-slate-500">
        Loading workspace…
      </div>
    );
  }

  const sendUser = () => {
    const t = draft.trim();
    if (!t) return;
    setExtras((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", body: t },
    ]);
    setDraft("");
    setTimeout(() => {
      setExtras((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "ai",
          title: "Swarm",
          body: "Placeholder reply — wire your model here.",
        },
      ]);
    }, 450);
  };

  if (config === null) {
    return (
      <div className="flex min-h-screen flex-1 items-center justify-center bg-white text-slate-500">
        Redirecting…
      </div>
    );
  }

  const allMessages = [...messages, ...extras];
  const sessionTitle =
    (config.sessionName ?? "").trim() || DEFAULT_SESSION_TITLE;

  return (
    <div className="flex h-dvh max-h-dvh w-full flex-col overflow-hidden bg-slate-50">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between border-b border-slate-200/80 bg-white px-4 py-3 sm:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#1DA1F2]">
            Current session
          </p>
          <h1 className="text-lg font-semibold text-slate-900 line-clamp-1">
            {sessionTitle}
          </h1>
          <p className="text-xs text-slate-500">
            {config.durationWeeks} wk · {config.classRatePerWeek}/wk ·{" "}
            {config.totalStudents} students
          </p>
        </div>
        <Link
          href="/"
          onClick={() => {
            clearConfig();
            try {
              localStorage.removeItem(LS_IMPORT_CURRICULUM);
              localStorage.removeItem(LS_IMPORT_CONTENT);
            } catch {
              // ignore storage failures
            }
          }}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-[#1DA1F2]/40 hover:text-[#1B8CD8]"
        >
          New Session
        </Link>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
        <aside className="flex w-full min-h-0 flex-1 basis-0 flex-col overflow-hidden border-b border-slate-200 bg-white lg:max-w-md lg:shrink-0 lg:basis-auto lg:flex-none lg:border-b-0 lg:border-r">
          <div
            ref={chatScrollRef}
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 sm:px-4"
          >
            <p className="mb-3 px-1 text-xs font-medium text-slate-500">
              AI swarm chat
            </p>
            <ul className="flex flex-col gap-3">
              {allMessages.map((m) => (
                <li
                  key={m.id}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "user" ? (
                    <div className="max-w-[90%] rounded-2xl rounded-br-md bg-sky-100 px-4 py-2 text-sm leading-relaxed text-slate-900 shadow-sm">
                      {m.body}
                    </div>
                  ) : m.role === "ai_card" ? (
                    <div className="max-w-[92%] overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-sm">
                      {m.title && (
                        <p className="border-b border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700">
                          {m.title}
                        </p>
                      )}
                      <div className="relative aspect-[4/3] bg-gradient-to-br from-sky-100 to-slate-100">
                        <Image
                          src="/report-placeholder.svg"
                          alt=""
                          fill
                          unoptimized
                          className="object-cover"
                          priority
                        />
                      </div>
                      <p className="px-3 py-2 text-xs leading-relaxed text-slate-600">
                        {m.body}
                      </p>
                    </div>
                  ) : (
                    <div className="max-w-[90%] rounded-2xl rounded-bl-md bg-slate-100 px-4 py-2 text-sm leading-relaxed text-slate-800 shadow-sm">
                      {m.title && (
                        <p className="mb-1 text-xs font-semibold text-[#1B8CD8]">
                          {m.title}
                        </p>
                      )}
                      {m.body}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="shrink-0 border-t border-slate-200 bg-white p-3 sm:p-4">
            <div className="flex gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-2 py-2 focus-within:border-[#1DA1F2]/35 focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1DA1F2]/15">
              <button
                type="button"
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-sky-50 hover:text-[#1DA1F2]"
                aria-label="Add attachment"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden
                >
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </button>
              <input
                className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                placeholder="Message the swarm…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendUser();
                  }
                }}
              />
              <button
                type="button"
                onClick={sendUser}
                className="shrink-0 rounded-xl bg-[#1DA1F2] px-3 py-2 text-sm font-semibold text-white hover:bg-[#1B8CD8]"
              >
                Send
              </button>
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 flex-1 basis-0 flex-col overflow-hidden bg-gradient-to-br from-white via-white to-sky-50/50 lg:flex-[1.4] lg:min-w-0">
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 sm:px-8 sm:py-8">
            <div className="mx-auto max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#1DA1F2]">
                Report
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                Curriculum feedback
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                Synthesized from simulated students and teachers. Replace this
                copy with live model output.
              </p>

              <section className="mt-8 space-y-4 rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">
                  Executive summary
                </h3>
                <p className="text-sm leading-relaxed text-slate-700">
                  Learners stay on track when week 3 is split into a conceptual
                  primer plus a hands-on lab. Higher Bloom levels land better if
                  each has a worked example tied to your stated content goals.
                </p>
                {config.content && (
                  <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">
                      Your content brief:{" "}
                    </span>
                    {config.content}
                  </div>
                )}
                {config.visionMission && (
                  <div className="rounded-xl bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-600">
                    <span className="font-semibold text-slate-800">
                      Vision &amp; mission:{" "}
                    </span>
                    {config.visionMission}
                  </div>
                )}
                {config.targetStudentsDescription && (
                  <div className="rounded-xl bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-600">
                    <span className="font-semibold text-slate-800">
                      Target students:{" "}
                    </span>
                    {config.targetStudentsDescription}
                  </div>
                )}
              </section>

              <section className="mt-6 grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-900">
                    Student signals
                  </h3>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
                    <li>
                      Mid-course engagement dips when readings stack without
                      checkpoints.
                    </li>
                    <li>
                      Project weeks need explicit rubrics—swarm graded
                      inconsistently without them.
                    </li>
                    <li>
                      Bloom mix: {(config.bloomLevels ?? []).join(", ") || "Not set"}
                      .
                    </li>
                  </ul>
                </div>
                <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm">
                  <div className="border-b border-slate-100 px-5 py-3">
                    <h3 className="text-sm font-semibold text-slate-900">
                      Visual takeaway
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">
                      Example figure slot for charts or diagrams from your swarm.
                    </p>
                  </div>
                  <div className="relative aspect-video bg-slate-100">
                    <Image
                      src="/report-chart.svg"
                      alt="Illustrative engagement chart placeholder"
                      fill
                      unoptimized
                      className="object-cover"
                    />
                  </div>
                </div>
              </section>

              <section className="mt-6 rounded-2xl border border-dashed border-[#1DA1F2]/35 bg-sky-50/40 p-5">
                <h3 className="text-sm font-semibold text-slate-900">
                  Next edits to try
                </h3>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-700">
                  <li>Add one low-stakes quiz after dense theory blocks.</li>
                  <li>Reserve two weeks labeled “studio / consolidation.”</li>
                  <li>Publish a single-page pacing map learners can skim.</li>
                </ol>
              </section>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
