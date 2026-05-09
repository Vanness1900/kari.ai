"""Peer contagion: adjust students after swarm (stub; runs after all students)."""

from __future__ import annotations

from copy import deepcopy

from orchestrator.state import ClassroomState


def run_peer_contagion(state: ClassroomState) -> dict:
    """Production: high-influence students nudge neighbours. Stub: no-op on traits."""
    students = [deepcopy(s) for s in state["students"]]
    mod = state["current_module"]
    step = state["current_timestep"]
    return {
        "students": students,
        "timestep_logs": [
            {
                "agent": "peer_contagion",
                "module_index": mod,
                "timestep": step,
                "payload": {"stub": True},
            }
        ],
    }
