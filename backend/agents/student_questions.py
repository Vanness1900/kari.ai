"""Student question round for QNA (timestep 2): one student raises their hand; teacher answers next."""

from __future__ import annotations

from llm.chat import choose_model, llm_json
from orchestrator.state import ClassroomState
from settings import get_settings


def _one_question(*, model: str, delivery: str, s: dict) -> dict | None:
    sid = str(s.get("id", "?"))
    name = str(s.get("name", "Student"))
    confusion = float(s.get("confusion_level", 0.0))
    anxious = float(s.get("social_anxiety", 0.0))

    system = (
        "You are a student in a classroom simulation. "
        "You are about to ask ONE clarifying question about the teacher's delivery."
    )
    user = (
        f"Student name: {name}\n"
        f"Current confusion_level: {confusion}\n"
        f"Social anxiety: {anxious}\n\n"
        "Teacher delivery (context):\n"
        f"{delivery}\n\n"
        "Return JSON with exactly this shape:\n"
        '{ "question": string | null }\n\n'
        "If you would not ask a question (too anxious / not confused), set question to null."
    )

    out = llm_json(model=model, system=system, user=user)
    text = out.get("question", None)
    if isinstance(text, str):
        text = text.strip()
    if not text:
        return None
    return {"student_id": sid, "name": name, "question": text}


def _pick_asker_order(students: list[dict]) -> list[dict]:
    """Most-likely-to-raise-hand first: high confusion, low social anxiety."""
    def score(s: dict) -> float:
        confusion = float(s.get("confusion_level", 0.0) or 0.0)
        anxious = float(s.get("social_anxiety", 0.0) or 0.0)
        return confusion - 0.3 * anxious
    return sorted(students, key=score, reverse=True)


def run_student_questions(state: ClassroomState) -> dict:
    """
    Pick a single student to raise their hand each QNA round.

    The most-confused, least-anxious learner asks first. If they decline (LLM returns
    null), we walk down the ranked list until someone asks — but only ONE question is
    appended to ``qna_student_questions`` per module. The teacher node consumes that
    single question on timestep 2 and answers it.
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    delivery = (state.get("module_delivery_snapshot") or "").strip()

    settings = get_settings()
    model = choose_model(settings.default_student_model, fallback=settings.default_reasoning_model)

    students = state["students"] or []
    asker: dict | None = None
    question: dict | None = None
    for s in _pick_asker_order(students):
        asker = s
        try:
            q = _one_question(model=model, delivery=delivery, s=s)
        except Exception:
            q = None
        if q:
            question = q
            break

    if question is None and asker is not None:
        question = {
            "student_id": str(asker.get("id", "?")),
            "name": str(asker.get("name", "Student")),
            "question": "Could you recap the core idea from the delivery in plain language?",
        }

    questions = [question] if question else []

    return {
        "qna_student_questions": questions,
        "timestep_logs": [
            {
                "agent": "student_questions",
                "module_index": mod,
                "timestep": step,
                "payload": {"questions": questions, "asker_id": question and question.get("student_id"), "model": model},
            }
        ],
    }
