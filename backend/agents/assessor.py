"""Assessor agent: scores students and records module progress (stub)."""

from __future__ import annotations

from statistics import mean

from orchestrator.state import ClassroomState


def run_assessor(state: ClassroomState) -> dict:
    """Aggregate student signals; write `ModuleResult` when closing a module timestep 5 (stub)."""
    mod = state["current_module"]
    step = state["current_timestep"]
    students = state["students"]
    confusions = [float(s.get("confusion_level", 0.0)) for s in students]
    avg_c = mean(confusions) if confusions else 0.0

    updates: dict = {
        "avg_confusion_last": avg_c,
        "timestep_logs": [
            {
                "agent": "assessor",
                "module_index": mod,
                "timestep": step,
                "payload": {"avg_confusion": avg_c, "stub": True},
            }
        ],
    }

    # At end of module cycle (timestep 5), emit a coarse module result (production: richer).
    if step >= 5:

        def _estimate_score(student: dict) -> float:
            ks = student.get("knowledge_state") or {}
            nums = [float(v) for v in ks.values() if isinstance(v, (int, float))]
            return sum(nums) / len(nums) if nums else 0.5

        scores = {str(s.get("id", idx)): _estimate_score(s) for idx, s in enumerate(students)}
        updates["module_results"] = [
            {
                "module_index": mod,
                "student_scores": scores,
                "at_risk_student_ids": [str(s.get("id")) for s in students if float(s.get("confusion_level", 0)) > 0.65],
                "notes": "stub module result",
            }
        ]

    return updates
