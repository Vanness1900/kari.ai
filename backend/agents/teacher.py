"""Teacher agent: generates lesson delivery for the current module/timestep (stub)."""

from __future__ import annotations

from llm.chat import llm_text
from orchestrator.state import ClassroomState
from settings import get_settings


def _phase_for_timestep(step: int) -> str:
    return {1: "deliver", 2: "qna", 3: "exercise", 4: "assess", 5: "update"}.get(
        step, "deliver"
    )


def run_teacher(state: ClassroomState) -> dict:
    """
    Produce `current_lesson` text. Real implementation will persist to Chroma via RAG layer.

    | step | phase     | notes                                          |
    |------|-----------|-----------------------------------------------|
    | 1    | deliver   | module content; snapshot for QNA              |
    | 2    | qna       | clarification; student questions + answers     |
    | 3    | exercise  | RAG on when wired                              |
    | 4    | assess    | RAG off                                        |
    | 5    | update    | recap / consolidation                         |
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    phase = _phase_for_timestep(step)
    modules = state["curriculum"].get("modules") or []
    module = modules[mod] if mod < len(modules) else {}
    title = module.get("title", f"Module {mod}")
    module_content = module.get("content", "")

    settings = get_settings()
    model = settings.default_teacher_model

    # Build a phase-specific user prompt.
    delivery_snapshot = (state.get("module_delivery_snapshot") or "").strip()
    q_rows = state.get("qna_student_questions") or []

    system = (
        "You are a helpful teacher in a classroom simulation. "
        "Write clear, structured lesson text suitable for students to read."
    )
    user = (
        f"Module title: {title}\n"
        f"Phase: {phase} (timestep {step}/5)\n\n"
        f"Module content (syllabus/slides summary, may be empty):\n{module_content}\n\n"
    )
    if step == 2:
        user += (
            "Earlier delivery snapshot (context):\n"
            f"{delivery_snapshot}\n\n"
            "Student questions:\n"
            + "\n".join([f"- {r.get('name','Student')}: {r.get('question','')}" for r in q_rows])
            + "\n\n"
            "Answer the questions concisely, referencing the delivery. Use headings and bullets."
        )
    elif step == 1:
        user += "Deliver the core concepts for this module in a teachable way (headings + examples)."
    elif step == 3:
        user += "Give 3 short practice exercises and worked solutions (exercise phase)."
    elif step == 4:
        user += "Give a short closed-book quiz (5 questions) and an answer key."
    elif step == 5:
        user += "Provide a recap and consolidation checklist + common pitfalls."

    try:
        lesson = llm_text(model=model, system=system, user=user)
        raw_ok = True
    except Exception as e:
        # Fallback to stub if keys/models aren't configured yet.
        lesson = f"[stub-fallback] {phase.upper()} — «{title}» (timestep {step}/5). LLM error: {e}"
        raw_ok = False

    updates: dict = {
        "current_lesson": lesson,
        "timestep_logs": [
            {
                "agent": "teacher",
                "module_index": mod,
                "timestep": step,
                "payload": {"phase": phase, "model": model, "llm_ok": raw_ok},
            }
        ],
    }
    if step == 1:
        updates["module_delivery_snapshot"] = lesson
    return updates
