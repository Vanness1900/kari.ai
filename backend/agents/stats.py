"""Stats logger: aggregates per-timestep and per-module metrics (non-LLM)."""

from __future__ import annotations

from statistics import mean

from orchestrator.state import ClassroomState


def run_stats(state: ClassroomState) -> dict:
    """
    Lightweight aggregation used every timestep.

    This is intentionally NOT the end-of-course assessor. It just records a few
    class-level metrics and (on timestep 5) emits a coarse ModuleResult stub.
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    students = state["students"]

    confusions = [float(s.get("confusion_level", 0.0)) for s in students]
    avg_c = mean(confusions) if confusions else 0.0

    updates: dict = {
        "avg_confusion_last": avg_c,
        "timestep_logs": [
            {
                "agent": "stats",
                "module_index": mod,
                "timestep": step,
                "payload": {"avg_confusion": avg_c, "stub": True},
            }
        ],
    }

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
                "at_risk_student_ids": [
                    str(s.get("id"))
                    for s in students
                    if float(s.get("confusion_level", 0)) > 0.65
                ],
                "notes": "stub module result",
            }
        ]

    return updates

