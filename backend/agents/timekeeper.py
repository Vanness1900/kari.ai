"""Timekeeper: pacing / clock (stub; extend for fatigue and schedule rules)."""

from __future__ import annotations

from orchestrator.state import ClassroomState


def run_timekeeper(state: ClassroomState) -> dict:
    mod = state["current_module"]
    step = state["current_timestep"]
    return {
        "timestep_logs": [
            {
                "agent": "timekeeper",
                "module_index": mod,
                "timestep": step,
                "payload": {"stub": True},
            }
        ],
    }
