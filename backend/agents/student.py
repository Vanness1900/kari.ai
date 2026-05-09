"""Student swarm: one agent per student (sequential orchestration; stub)."""

from __future__ import annotations

from copy import deepcopy

from orchestrator.state import ClassroomState


def run_student_swarm(state: ClassroomState) -> dict:
    """
    Run all students for the current timestep. Production: sequential calls, no asyncio.gather
    (rate limits). Stubs copy students and append logs.
    """
    mod = state["current_module"]
    step = state["current_timestep"]
    students = [deepcopy(s) for s in state["students"]]
    logs: list[dict] = []
    for s in students:
        sid = s.get("id", "?")
        # Stub reaction; real agent returns JSON matching CLAUDE.md schema.
        s["confusion_level"] = float(s.get("confusion_level", 0.25))
        s["attention_remaining"] = float(s.get("attention_remaining", 0.8))
        logs.append(
            {
                "agent": "student",
                "module_index": mod,
                "timestep": step,
                "payload": {"student_id": sid, "stub": True},
            }
        )
    return {"students": students, "timestep_logs": logs}
