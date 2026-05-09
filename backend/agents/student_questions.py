"""Student question round for QNA (timestep 2): each learner asks; teacher answers in the next node."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

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


def run_student_questions(state: ClassroomState) -> dict:
    """
    Sequential pass: each student proposes a clarifying question about ``module_delivery_snapshot``.
    Results are merged into ``qna_student_questions`` for ``run_teacher`` (Q&A lesson text).
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    delivery = (state.get("module_delivery_snapshot") or "").strip()
    questions: list[dict] = []

    settings = get_settings()
    model = choose_model(settings.default_student_model, fallback=settings.default_reasoning_model)

    if settings.enable_parallel_students and len(state["students"]) > 1:
        max_workers = max(1, int(settings.max_concurrency))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [
                ex.submit(_one_question, model=model, delivery=delivery, s=s)
                for s in state["students"]
            ]
            for fut in as_completed(futures):
                try:
                    q = fut.result()
                    if q:
                        questions.append(q)
                except Exception:
                    # ignore; we’ll fall back below if needed
                    pass
    else:
        for s in state["students"]:
            try:
                q = _one_question(model=model, delivery=delivery, s=s)
                if q:
                    questions.append(q)
            except Exception:
                pass

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
                "payload": {"questions": questions, "model": model},
            }
        ],
    }
