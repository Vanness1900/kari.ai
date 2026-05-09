"""Insight agent: end-of-simulation curriculum critique (stub; single expensive call in prod)."""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_insight(state: ClassroomState) -> dict:
    """Summarize assessments + logs for curriculum designer (stub)."""
    n_mod = len(state["curriculum"].get("modules") or [])
    assessments = state.get("student_assessments") or {}
    scores = [float(a.get("overall_score", 0.0)) for a in assessments.values()]
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    at_risk = [
        sid
        for sid, a in assessments.items()
        if a.get("risk_flags") and len(a.get("risk_flags") or []) > 0
    ]
    report = {
        "summary": (
            f"[stub] Insight over {n_mod} module(s) and {len(assessments)} student assessment(s). "
            f"Avg score≈{avg_score:.2f}. At-risk={len(at_risk)}."
        ),
        "curriculum_critique": (
            "stub: summarize pain points from QNA + exercise + assess phases; "
            "flag ordering/pacing/Bloom mismatches for the curriculum designer."
        ),
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
                "payload": {"stub": True, "assessed_students": len(assessments)},
            }
        ],
    }
