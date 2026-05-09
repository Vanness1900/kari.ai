"""Student swarm: one agent per student (sequential orchestration; stub)."""

from __future__ import annotations

from copy import deepcopy

from orchestrator.state import ClassroomState


def run_student_swarm(state: ClassroomState) -> dict:
    """
    Run all students for the current timestep. Production: sequential calls, no asyncio.gather
    (rate limits). Stubs copy students and append logs.

    Timestep 2: students react to the teacher's Q&A text in ``current_lesson`` (after ask → answer).
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    lesson_excerpt = (state.get("current_lesson") or "")[:200]
    students = [deepcopy(s) for s in state["students"]]
    logs: list[dict] = []
    for s in students:
        sid = s.get("id", "?")
        # Stub reaction; real agent returns JSON matching CLAUDE.md schema.
        conf = float(s.get("confusion_level", 0.25))
        if step == 2:
            conf = max(0.0, conf - 0.08)
        s["confusion_level"] = conf
        attn = float(s.get("attention_remaining", 0.8))
        s["attention_remaining"] = attn
        ks = s.get("knowledge_state") or {}
        mastery_vals = [float(v) for v in ks.values() if isinstance(v, (int, float))]
        mastery_avg = (sum(mastery_vals) / len(mastery_vals)) if mastery_vals else 0.0
        logs.append(
            {
                "agent": "student",
                "module_index": mod,
                "timestep": step,
                "payload": {
                    "student_id": sid,
                    "stub": True,
                    "heard_teacher_qna": step == 2,
                    "lesson_excerpt": lesson_excerpt,
                    "confusion_level": conf,
                    "attention_remaining": attn,
                    "knowledge_mastery_avg": mastery_avg,
                },
            }
        )
    return {"students": students, "timestep_logs": logs}
