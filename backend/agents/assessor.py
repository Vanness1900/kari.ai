"""Assessor agent: end-of-course per-student assessment (stub)."""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_assessor(state: ClassroomState) -> dict:
    """
    End-of-course assessor phase.

    Runs once per student, sequentially, after all modules/timesteps complete.
    Each invocation assesses exactly one student (index = state["assessor_index"]).
    """
    idx = int(state.get("assessor_index", 0))
    students = state["students"]
    if idx >= len(students):
        return {
            "timestep_logs": [
                {
                    "agent": "assessor",
                    "module_index": state["current_module"],
                    "timestep": state["current_timestep"],
                    "payload": {"done": True, "stub": True},
                }
            ]
        }

    s = students[idx]
    sid = str(s.get("id", idx))
    name = str(s.get("name", "Student"))

    ks = s.get("knowledge_state") or {}
    nums = [float(v) for v in ks.values() if isinstance(v, (int, float))]
    overall = sum(nums) / len(nums) if nums else 0.5

    risk_flags: list[str] = []
    if float(s.get("confusion_level", 0.0)) > 0.65:
        risk_flags.append("high_confusion")
    if float(s.get("attention_remaining", 1.0)) < 0.25:
        risk_flags.append("low_attention")

    record = {
        "student_id": sid,
        "overall_score": float(overall),
        "risk_flags": risk_flags,
        "narrative": f"[stub] {name} ended with score≈{overall:.2f}. Flags={risk_flags or ['none']}.",
    }

    existing = state.get("student_assessments") or {}
    merged = {**existing, sid: record}

    return {
        "student_assessments": merged,
        "assessor_index": idx + 1,
        "timestep_logs": [
            {
                "agent": "assessor",
                "module_index": state["current_module"],
                "timestep": state["current_timestep"],
                "payload": {"student_id": sid, "assessor_index": idx, "stub": True},
            }
        ],
    }
