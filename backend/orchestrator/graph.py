"""LangGraph orchestration glue (Phase 2 minimal stub).

This file intentionally does NOT call any LLMs yet. It's only here so the FastAPI
route can execute end-to-end while we build out the real nodes:
timekeeper → teacher → student_swarm → (router/loop) → assessor → insight.
"""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_simulation(state: ClassroomState) -> ClassroomState:
    """Temporary stub runner.

    Phase 2 goal: provide a stable place for the real LangGraph graph.
    For now, we mark the simulation complete and return a minimally shaped result.
    """
    # Create a shallow copy so callers don't accidentally hold a reference.
    final: ClassroomState = dict(state)  # type: ignore[assignment]

    final["simulation_complete"] = True

    # Ensure required collections exist even if caller passed partial state.
    final.setdefault("timestep_logs", [])
    final.setdefault("module_results", [])

    # Minimal module result so the API can report counts.
    final["module_results"].append(
        {
            "module_index": final.get("current_module", 0),
            "headline": "Stub run completed (no LLMs yet).",
        }
    )

    return final

