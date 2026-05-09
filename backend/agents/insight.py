"""Insight agent: end-of-simulation curriculum critique (stub; single expensive call in prod)."""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_insight(state: ClassroomState) -> dict:
    """Consume `module_results` / history; production uses heavy reasoning model."""
    n_mod = len(state["curriculum"].get("modules") or [])
    report = {
        "summary": f"[stub] Insight over {n_mod} module(s). Wire LLM + optional GPT Image 2 here.",
        "curriculum_critique": "stub: ordering, Bloom alignment, pacing — not yet generated.",
        "blooms_alignment_notes": [],
    }
    return {
        "insight_report": report,
        "simulation_complete": True,
        "timestep_logs": [
            {
                "agent": "insight",
                "module_index": state["current_module"],
                "timestep": state["current_timestep"],
                "payload": {"stub": True},
            }
        ],
    }
