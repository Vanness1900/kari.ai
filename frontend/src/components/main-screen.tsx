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

type ChatItemKind = "message" | "log";
type ChatAuthor = "user" | "ai";
type LogStatus = "running" | "done";

type ChatItem = {
  id: string;
  kind: ChatItemKind;
  author?: ChatAuthor;
  title?: string;
  body: string;
  status?: LogStatus;
};

type StudentPersona = {
  id: string;
  name: string;
  avatarSrc: string;
  lines: string[];
};

function useStableId() {
  const n = useRef(0);
  return () => `${Date.now()}-${++n.current}`;
}

function HoverFadeAvatar({
  ariaLabel,
  frontClassName,
  ringClassName,
  imageSrc,
  imageAlt,
  sizeClassName,
  name,
  speech,
}: {
  ariaLabel: string;
  frontClassName: string;
  ringClassName: string;
  imageSrc: string;
  imageAlt: string;
  sizeClassName: string;
  name: string;
  speech?: string | null;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      className="relative flex flex-col items-center"
      aria-label={ariaLabel}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {speech ? (
        <div className="pointer-events-none absolute -top-10 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-xl border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-sm">
          {speech}
          <span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-slate-200 bg-white" />
        </div>
      ) : null}

      <div className={sizeClassName}>
        <div className="relative h-full w-full">
          <div
            className={`absolute inset-0 rounded-full ring-2 transition-opacity duration-300 ease-in-out ${
              hovered ? "opacity-0" : "opacity-100"
            } ${ringClassName} ${frontClassName}`}
          />
          <div
            className={`absolute inset-0 overflow-hidden rounded-full ring-2 transition-opacity duration-300 ease-in-out ${
              hovered ? "opacity-100" : "opacity-0"
            } ${ringClassName}`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- local static assets */}
            <img src={imageSrc} alt={imageAlt} className="h-full w-full object-cover" />
          </div>
        </div>
      </div>

      <div
        className={`mt-1 w-full text-center text-[11px] font-semibold text-slate-700 transition-opacity ${
          hovered ? "opacity-100" : "opacity-0"
        }`}
      >
        {name}
      </div>
    </div>
  );
}

function SimulationLoadingScene({
  phaseLabel,
}: {
  phaseLabel: string;
}) {
  const students: StudentPersona[] = useMemo(
    () => [
      {
        id: "s1",
        name: "Kai",
        avatarSrc: "/student-placeholder.svg",
        lines: ["boring…", "zzz", "wait what", "I’m lost"],
      },
      {
        id: "s2",
        name: "Mina",
        avatarSrc: "/student-placeholder.svg",
        lines: ["doing good teach", "nice example", "ok I get it"],
      },
      {
        id: "s3",
        name: "Rafi",
        avatarSrc: "/student-placeholder.svg",
        lines: ["speed up pls", "can we try a quiz?", "more practice"],
      },
      {
        id: "s4",
        name: "Noor",
        avatarSrc: "/student-placeholder.svg",
        lines: ["I love this", "this makes sense", "keep going"],
      },
      {
        id: "s5",
        name: "Ivy",
        avatarSrc: "/student-placeholder.svg",
        lines: ["can you repeat?", "example again?", "slowww"],
      },
      {
        id: "s6",
        name: "Jae",
        avatarSrc: "/student-placeholder.svg",
        lines: ["W", "solid", "this is cool"],
      },
      {
        id: "s7",
        name: "Sora",
        avatarSrc: "/student-placeholder.svg",
        lines: ["I’m taking notes", "good pacing", "clean explanation"],
      },
      {
        id: "s8",
        name: "Leo",
        avatarSrc: "/student-placeholder.svg",
        lines: ["huh", "I missed that", "one more time"],
      },
      {
        id: "s9",
        name: "Tess",
        avatarSrc: "/student-placeholder.svg",
        lines: ["can we branch out?", "try a group activity", "let’s discuss"],
      },
      {
        id: "s10",
        name: "Omar",
        avatarSrc: "/student-placeholder.svg",
        lines: ["ok ok", "makes sense", "let’s go"],
      },
    ],
    [],
  );

  const [activeSpeech, setActiveSpeech] = useState<{
    studentId: string;
    text: string;
    nonce: number;
  } | null>(null);

  useEffect(() => {
    let alive = true;
    const pick = () => {
      const student = students[Math.floor(Math.random() * students.length)];
      const text = student.lines[Math.floor(Math.random() * student.lines.length)];
      setActiveSpeech({ studentId: student.id, text, nonce: Date.now() });
      window.setTimeout(() => {
        if (!alive) return;
        setActiveSpeech((prev) =>
          prev && prev.studentId === student.id ? null : prev,
        );
      }, 1400);
    };

    const id = window.setInterval(() => {
      if (Math.random() < 0.35) pick();
    }, 1500);

    const first = window.setTimeout(pick, 900);

    return () => {
      alive = false;
      window.clearInterval(id);
      window.clearTimeout(first);
    };
  }, [students]);

  return (
    <div className="rounded-3xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#1DA1F2]">
            Class simulation
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
            {phaseLabel}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Hover students to flip and reveal who’s in the room.
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-mono text-slate-600">
          live
        </div>
      </div>

      <div className="mt-6 rounded-3xl border border-slate-200 bg-white p-4 sm:p-5">
        <div className="flex flex-col items-center">
          <HoverFadeAvatar
            ariaLabel="Teacher"
            frontClassName="bg-[#1DA1F2]/10"
            ringClassName="ring-slate-200"
            imageSrc="/student-placeholder.svg"
            imageAlt="Teacher"
            sizeClassName="h-14 w-14 sm:h-16 sm:w-16 mb-2 md:mb-6"
            name="Teacher"
          />
        </div>

        <div className="mt-8">
          <div className="grid grid-cols-5 gap-x-4 gap-y-7 sm:gap-x-6 sm:gap-y-9">
            {students.map((s) => (
              <HoverFadeAvatar
                key={s.id}
                ariaLabel={`${s.name} (student)`}
                frontClassName="bg-[#1DA1F2]/15"
                ringClassName="ring-[#1DA1F2]/25"
                imageSrc={s.avatarSrc}
                imageAlt={s.name}
                sizeClassName="h-12 w-12 sm:h-14 sm:w-14"
                name={s.name}
                speech={activeSpeech?.studentId === s.id ? activeSpeech.text : null}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
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
  const nextId = useStableId();
  const runOnceRef = useRef(false);
  const timersRef = useRef<number[]>([]);
  const shouldAutoScrollRef = useRef(true);

  useEffect(() => {
    const c = loadConfig();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load from sessionStorage after mount
    setConfig(c);
    if (!c && !didRedirectRef.current) {
      didRedirectRef.current = true;
      router.replace("/");
    }
  }, [router]);

  const [items, setItems] = useState<ChatItem[]>([]);
  const runningStepLabel = useMemo(() => {
    for (let i = items.length - 1; i >= 0; i -= 1) {
      const it = items[i];
      if (it.kind === "log" && it.status === "running") return it.body;
    }
    return "";
  }, [items]);

  const showSimulationScene = useMemo(() => {
    const s = runningStepLabel.toLowerCase();
    if (!s) return false;
    // Show the interactive loading scene from the very beginning of the run
    // up through the end of "Assessing result". Once "Generating feedback" starts,
    // we switch back to the report.
    if (s.includes("generating feedback")) return false;
    return true;
  }, [runningStepLabel]);

  const clearTimers = () => {
    for (const id of timersRef.current) window.clearTimeout(id);
    timersRef.current = [];
  };

  const sleep = (ms: number) =>
    new Promise<void>((resolve) => {
      const id = window.setTimeout(() => resolve(), ms);
      timersRef.current.push(id);
    });

  const startLogStep = (text: string) => {
    setItems((prev) => {
      const next = prev.map((x) =>
        x.kind === "log" && x.status === "running"
          ? { ...x, status: "done" as const }
          : x,
      );
      next.push({
        id: nextId(),
        kind: "log",
        body: text,
        status: "running" as const,
      });
      return next;
    });
  };

  const finishLogStep = () => {
    setItems((prev) => {
      const idxFromEnd = [...prev]
        .reverse()
        .findIndex((x) => x.kind === "log" && x.status === "running");
      if (idxFromEnd === -1) return prev;
      const idx = prev.length - 1 - idxFromEnd;
      return prev.map((x, i) =>
        i === idx ? { ...x, status: "done" as const } : x,
      );
    });
  };

  const pushAiMessage = (title: string | undefined, body: string) => {
    setItems((prev) => [
      ...prev,
      { id: nextId(), kind: "message", author: "ai", title, body },
    ]);
  };

  const pushUserMessage = (body: string) => {
    setItems((prev) => [
      ...prev,
      { id: nextId(), kind: "message", author: "user", body },
    ]);
  };

  useEffect(() => {
    if (!config) return;
    if (runOnceRef.current) return;
    runOnceRef.current = true;

    let cancelled = false;
    clearTimers();
    setItems([]);

    const title = config.curriculum?.trim() || "your curriculum";

    const run = async () => {
      pushAiMessage(
        "Swarm",
        `Got it. I’ll run a class simulation for “${title}” and generate feedback. Follow along in the logs.`,
      );

      startLogStep("Orchestrating class simulation");
      await sleep(350);
      finishLogStep();

      startLogStep("Generating time keeper");
      await sleep(280);
      finishLogStep();

      startLogStep("Generating teacher");
      await sleep(280);
      finishLogStep();

      startLogStep("Generating assessor");
      await sleep(280);
      finishLogStep();

      startLogStep("Generating students");
      await sleep(320);
      finishLogStep();

      startLogStep("Simulating (branch out)");
      await sleep(90800);
      finishLogStep();

      startLogStep("Assessing result");
      await sleep(1200);
      finishLogStep();

      startLogStep("Generating feedback");
      await sleep(1200);
      finishLogStep();

      if (cancelled) return;
      pushAiMessage(
        "Swarm",
        "Done. Your report is ready on the right — tell me which week or outcome you want to stress-test next.",
      );
    };

    run().catch(() => {
      if (cancelled) return;
      pushAiMessage(
        "Swarm",
        "Something went wrong while running the simulation steps. Try generating again.",
      );
    });

    return () => {
      cancelled = true;
      clearTimers();
    };
  }, [config]);

  useEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    /**
     * Only auto-scroll if the user is already near the bottom.
     * This prevents layout-jitter (scrollbar + width changes) from affecting the
     * right-side hover interactions.
     */
    if (shouldAutoScrollRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [items]);

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
    pushUserMessage(t);
    setDraft("");
    const id = window.setTimeout(() => {
      pushAiMessage(
        "Swarm",
        "I’m still running on a placeholder UI — wire a real model call here next.",
      );
    }, 450);
    timersRef.current.push(id);
  };

  if (config === null) {
    return (
      <div className="flex min-h-screen flex-1 items-center justify-center bg-white text-slate-500">
        Redirecting…
      </div>
    );
  }

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
            className="min-h-0 flex-1 overflow-y-scroll overscroll-contain px-3 py-4 sm:px-4"
            style={{ scrollbarGutter: "stable" }}
            onScroll={() => {
              const el = chatScrollRef.current;
              if (!el) return;
              const distanceFromBottom =
                el.scrollHeight - el.scrollTop - el.clientHeight;
              shouldAutoScrollRef.current = distanceFromBottom < 80;
            }}
          >
            <p className="mb-3 px-1 text-xs font-medium text-slate-500">
              AI swarm chat
            </p>
            <ul className="flex flex-col gap-3">
              {items.map((m) => (
                <li
                  key={m.id}
                  className={`flex ${
                    m.kind === "message" && m.author === "user"
                      ? "justify-end"
                      : "justify-start"
                  }`}
                >
                  {m.kind === "log" ? (
                    <div className="pointer-events-none max-w-[92%] rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 shadow-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex h-4 w-4 items-center justify-center rounded-full border ${
                            m.status === "running"
                              ? "border-[#1DA1F2]/35 bg-sky-50 text-[#1B8CD8]"
                              : "border-slate-200 bg-white text-slate-400"
                          }`}
                          aria-hidden
                        >
                          {m.status === "running" ? "…" : "✓"}
                        </span>
                        <span className="font-mono">{m.body}</span>
                      </div>
                    </div>
                  ) : m.author === "user" ? (
                    <div className="pointer-events-none max-w-[90%] rounded-2xl rounded-br-md bg-sky-100 px-4 py-2 text-sm leading-relaxed text-slate-900 shadow-sm">
                      {m.body}
                    </div>
                  ) : (
                    <div className="pointer-events-none max-w-[90%] rounded-2xl rounded-bl-md bg-slate-100 px-4 py-2 text-sm leading-relaxed text-slate-800 shadow-sm">
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
              {showSimulationScene ? (
                <SimulationLoadingScene
                  phaseLabel={runningStepLabel || "Simulating…"}
                />
              ) : (
                <>
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
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
