"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LiveSimulationView } from "@/components/simulation/live-simulation-view";

const SESSION_KEY = "kari-session-id";

export function MainWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [sessionId, setSessionId] = useState<string | null | undefined>(
    undefined,
  );

  useEffect(() => {
    const fromQuery = searchParams.get("session");
    if (fromQuery) {
      try {
        sessionStorage.setItem(SESSION_KEY, fromQuery);
      } catch {
        // ignore storage failures — query param still works for this tab
      }
      // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate after mount
      setSessionId(fromQuery);
      return;
    }
    let stored: string | null = null;
    try {
      stored = sessionStorage.getItem(SESSION_KEY);
    } catch {
      stored = null;
    }
    if (stored) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate after mount
      setSessionId(stored);
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- redirect when no session
    setSessionId(null);
    router.replace("/");
  }, [searchParams, router]);

  if (sessionId === undefined) {
    return (
      <div className="flex min-h-screen flex-1 items-center justify-center bg-slate-50 text-sm text-slate-500">
        Loading workspace…
      </div>
    );
  }
  if (!sessionId) {
    return (
      <div className="flex min-h-screen flex-1 items-center justify-center bg-white text-sm text-slate-500">
        Redirecting…
      </div>
    );
  }
  return <LiveSimulationView sessionId={sessionId} />;
}
