"""Insight agent: end-of-simulation curriculum critique (stub; single expensive call in prod)."""

from __future__ import annotations

from llm.chat import llm_text
from orchestrator.state import ClassroomState
from settings import get_settings


def run_insight(state: ClassroomState) -> dict:
    """Summarize assessments + logs for curriculum designer (LLM, single call)."""
    n_mod = len(state["curriculum"].get("modules") or [])
    assessments = state.get("student_assessments") or {}
    scores = [float(a.get("overall_score", 0.0)) for a in assessments.values()]
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    at_risk = [
        sid
        for sid, a in assessments.items()
        if a.get("risk_flags") and len(a.get("risk_flags") or []) > 0
    ]
    settings = get_settings()
    model = settings.default_reasoning_model

    system = (
        "You are an insight agent helping a curriculum designer improve a course. "
        "You receive per-student assessments and module summaries from a simulation. "
        "Be specific, actionable, and structured."
    )
    user = (
        f"Curriculum:\n{state.get('curriculum')}\n\n"
        f"Module results:\n{state.get('module_results')}\n\n"
        f"Student assessments (per student):\n{assessments}\n\n"
        "Write:\n"
        "1) A short executive summary (3-5 bullets)\n"
        "2) Curriculum critique: ordering/pacing/Bloom alignment\n"
        "3) 3-6 concrete changes to make\n"
        "4) Bloom alignment notes as bullet list\n"
        "Return plain text (no JSON)."
    )

    llm_ok = True
    try:
        critique = llm_text(model=model, system=system, user=user)
    except Exception as e:
        llm_ok = False
        critique = f"[stub-fallback] Insight generation failed: {e}"

    report = {
        "summary": (
            f"Insight over {n_mod} module(s) and {len(assessments)} student assessment(s). "
            f"Avg score≈{avg_score:.2f}. At-risk={len(at_risk)}.\n\n{critique}"
        ),
        "curriculum_critique": critique,
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
                "payload": {
                    "assessed_students": len(assessments),
                    "model": model,
                    "llm_ok": llm_ok,
                },
            }
        ],
    }
