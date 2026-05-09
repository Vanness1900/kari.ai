"""Teacher agent: generates lesson delivery for the current module/timestep (stub)."""

from __future__ import annotations

from orchestrator.state import ClassroomState


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
    title = modules[mod].get("title", f"Module {mod}") if mod < len(modules) else f"Module {mod}"

    if step == 2:
        delivery = (state.get("module_delivery_snapshot") or "").strip()
        q_rows = state.get("qna_student_questions") or []
        blocks: list[str] = [
            f"## Q&A (phase 2) — «{title}»\n",
            "### Earlier delivery (context)\n",
            (delivery or "[No delivery snapshot yet — answer generically.]") + "\n\n",
            "### Discussion\n",
        ]
        for row in q_rows:
            who = row.get("name", "Student")
            q = row.get("question", "")
            blocks.append(f"**{who} asks:** {q}\n\n")
            blocks.append(
                f"**Teacher:** Let's clarify that directly. "
                f"I'll tie it back to the definition we used in delivery and give a quick example "
                f"so the class stays aligned.\n\n"
            )
        if not q_rows:
            blocks.append(
                "**Teacher:** I'll restate the main point from delivery and invite follow-ups.\n\n"
            )
        lesson = "".join(blocks)
    elif step == 1:
        lesson = (
            f"[stub] DELIVER — «{title}» (phase 1/5). "
            "Replace with LLM-generated delivery; Chroma storage handled by RAG teammate."
        )
    elif step == 3:
        lesson = (
            f"[stub] EXERCISE — «{title}» (phase 3/5). "
            "RAG on when wired; students retrieve slide chunks for practice."
        )
    elif step == 4:
        lesson = (
            f"[stub] ASSESS — «{title}» (phase 4/5). "
            "RAG off — closed-book style prompts."
        )
    elif step == 5:
        lesson = (
            f"[stub] UPDATE — «{title}» (phase 5/5). "
            "Recap / consolidation for this module."
        )
    else:
        lesson = f"[stub] «{title}» — segment {step}/5 (unexpected step; treat as delivery)."

    updates: dict = {
        "current_lesson": lesson,
        "timestep_logs": [
            {
                "agent": "teacher",
                "module_index": mod,
                "timestep": step,
                "payload": {"stub": True, "phase": phase},
            }
        ],
    }
    if step == 1:
        updates["module_delivery_snapshot"] = lesson
    return updates
