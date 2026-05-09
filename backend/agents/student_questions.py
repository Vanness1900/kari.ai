"""Student question round for QNA (timestep 2): each learner asks; teacher answers in the next node."""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_student_questions(state: ClassroomState) -> dict:
    """
    Sequential pass: each student proposes a clarifying question about ``module_delivery_snapshot``.
    Results are merged into ``qna_student_questions`` for ``run_teacher`` (Q&A lesson text).
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    delivery = (state.get("module_delivery_snapshot") or "").strip()
    questions: list[dict] = []

    for s in state["students"]:
        sid = str(s.get("id", "?"))
        name = str(s.get("name", "Student"))
        confusion = float(s.get("confusion_level", 0.0))
        anxious = float(s.get("social_anxiety", 0.0))

        if anxious > 0.7 and confusion < 0.5:
            text = ""
        elif confusion >= 0.45:
            text = (
                f"I'm stuck on how this connects to what we already learned—"
                f"could you walk through it once more slowly?"
            )
        elif confusion >= 0.25:
            text = (
                "Could you define the key term you used and give one short example?"
                if delivery
                else "What should we focus on first in this module?"
            )
        else:
            text = "Can you confirm the main takeaway in one sentence?"

        if text:
            questions.append(
                {
                    "student_id": sid,
                    "name": name,
                    "question": text,
                }
            )

    if not questions and state["students"]:
        s0 = state["students"][0]
        questions.append(
            {
                "student_id": str(s0.get("id", "?")),
                "name": str(s0.get("name", "Student")),
                "question": "Could you recap the core idea from the delivery in plain language?",
            }
        )

    return {
        "qna_student_questions": questions,
        "timestep_logs": [
            {
                "agent": "student_questions",
                "module_index": mod,
                "timestep": step,
                "payload": {"questions": questions, "stub": True},
            }
        ],
    }
