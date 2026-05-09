"""Teacher agent: generates lesson delivery for the current module/timestep (stub)."""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_teacher(state: ClassroomState) -> dict:
    """
    Produce `current_lesson` text. Real implementation will persist to Chroma via RAG layer.
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    modules = state["curriculum"].get("modules") or []
    title = modules[mod].get("title", f"Module {mod}") if mod < len(modules) else f"Module {mod}"
    lesson = (
        f"[stub] Delivering «{title}» — segment {step}/5. "
        "Replace with LLM-generated delivery; Chroma storage handled by RAG teammate."
    )
    return {
        "current_lesson": lesson,
        "timestep_logs": [
            {
                "agent": "teacher",
                "module_index": mod,
                "timestep": step,
                "payload": {"stub": True},
            }
        ],
    }
