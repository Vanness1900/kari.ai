"use client";

import { useEffect, useRef, useState } from "react";
import {
  type ClassroomState,
  type EventsResponse,
  type StatusResponse,
  type TimestepLog,
  getEvents,
  getState,
  getStatus,
} from "./api";

export type LiveSnapshot = {
  status: StatusResponse | null;
  events: TimestepLog[];
  state: ClassroomState | null;
  error: string | null;
  /** True the moment the latest status reports complete=true (use to redirect to /report). */
  isComplete: boolean;
};

const POLL_MS = 2000;

/**
 * Polls /status every 2s. Pulls /events incrementally (delta only). Pulls full /state
 * whenever the timestep advances (cheaper than re-shipping the whole state every tick).
 */
export function useSimulationLive(sessionId: string | null): LiveSnapshot {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [events, setEvents] = useState<TimestepLog[]>([]);
  const [state, setState] = useState<ClassroomState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sinceRef = useRef(0);
  const lastPhaseRef = useRef<string>("");
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!sessionId) return;
    stoppedRef.current = false;
    sinceRef.current = 0;
    lastPhaseRef.current = "";
    setStatus(null);
    setEvents([]);
    setState(null);
    setError(null);

    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      if (stoppedRef.current) return;
      try {
        const next = await getStatus(sessionId);
        setStatus(next);

        if (next.log_count > sinceRef.current) {
          const delta: EventsResponse = await getEvents(
            sessionId,
            sinceRef.current,
          );
          if (delta.events.length > 0) {
            setEvents((prev) => prev.concat(delta.events));
            sinceRef.current = delta.next_since;
          }
        }

        const phaseKey = `${next.current_module}:${next.current_timestep}:${next.simulation_complete ? "done" : "live"}`;
        if (phaseKey !== lastPhaseRef.current) {
          lastPhaseRef.current = phaseKey;
          try {
            const fresh = await getState(sessionId);
            setState(fresh);
          } catch (e) {
            // stale snapshot is fine; surface only persistent errors
            setError(e instanceof Error ? e.message : String(e));
          }
        }

        if (next.simulation_complete) {
          stoppedRef.current = true;
          return;
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!stoppedRef.current) {
          timer = setTimeout(tick, POLL_MS);
        }
      }
    };

    void tick();
    return () => {
      stoppedRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId]);

  return {
    status,
    events,
    state,
    error,
    isComplete: !!status?.simulation_complete,
  };
}
